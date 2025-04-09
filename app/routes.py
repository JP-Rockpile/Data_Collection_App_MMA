from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from .models import db, Fighter, Event, Fight

# Create blueprint
api = Blueprint('api', __name__)

# Error handler for 404 errors
@api.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

# Error handler for 400 errors
@api.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

# Error handler for 500 errors
@api.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Fighter routes
@api.route('/fighters', methods=['GET'])
def get_fighters():
    fighters = Fighter.query.all()
    return jsonify([fighter.to_dict() for fighter in fighters])

@api.route('/fighters/<int:id>', methods=['GET'])
def get_fighter(id):
    fighter = Fighter.query.get_or_404(id)
    return jsonify(fighter.to_dict())

@api.route('/fighters', methods=['POST'])
def create_fighter():
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400
    
    data = request.json
    
    # Validate required fields
    if 'first_name' not in data or 'last_name' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    fighter = Fighter(
        first_name=data['first_name'],
        last_name=data['last_name'],
        nickname=data.get('nickname'),
        height=data.get('height'),
        reach=data.get('reach')
    )
    
    try:
        db.session.add(fighter)
        db.session.commit()
        return jsonify(fighter.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Could not create fighter'}), 400

@api.route('/fighters/<int:id>', methods=['PUT'])
def update_fighter(id):
    fighter = Fighter.query.get_or_404(id)
    
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400
    
    data = request.json
    
    # Update fields
    if 'first_name' in data:
        fighter.first_name = data['first_name']
    if 'last_name' in data:
        fighter.last_name = data['last_name']
    if 'nickname' in data:
        fighter.nickname = data['nickname']
    if 'height' in data:
        fighter.height = data['height']
    if 'reach' in data:
        fighter.reach = data['reach']
    
    try:
        db.session.commit()
        return jsonify(fighter.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Could not update fighter'}), 400

@api.route('/fighters/<int:id>', methods=['DELETE'])
def delete_fighter(id):
    fighter = Fighter.query.get_or_404(id)
    
    try:
        db.session.delete(fighter)
        db.session.commit()
        return jsonify({'result': True})
    except:
        db.session.rollback()
        return jsonify({'error': 'Could not delete fighter'}), 400

# Event routes
@api.route('/events', methods=['GET'])
def get_events():
    events = Event.query.all()
    return jsonify([event.to_dict() for event in events])

@api.route('/events/<int:id>', methods=['GET'])
def get_event(id):
    event = Event.query.get_or_404(id)
    return jsonify(event.to_dict())

@api.route('/events', methods=['POST'])
def create_event():
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400
    
    data = request.json
    
    # Validate required fields
    if 'event_name' not in data or 'event_date' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        event_date = datetime.fromisoformat(data['event_date'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DD)'}), 400
    
    event = Event(
        event_name=data['event_name'],
        event_date=event_date,
        location=data.get('location')
    )
    
    try:
        db.session.add(event)
        db.session.commit()
        return jsonify(event.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Could not create event'}), 400

@api.route('/events/<int:id>', methods=['PUT'])
def update_event(id):
    event = Event.query.get_or_404(id)
    
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400
    
    data = request.json
    
    # Update fields
    if 'event_name' in data:
        event.event_name = data['event_name']
    if 'event_date' in data:
        try:
            event.event_date = datetime.fromisoformat(data['event_date'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DD)'}), 400
    if 'location' in data:
        event.location = data['location']
    
    try:
        db.session.commit()
        return jsonify(event.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Could not update event'}), 400

@api.route('/events/<int:id>', methods=['DELETE'])
def delete_event(id):
    event = Event.query.get_or_404(id)
    
    try:
        db.session.delete(event)
        db.session.commit()
        return jsonify({'result': True})
    except:
        db.session.rollback()
        return jsonify({'error': 'Could not delete event'}), 400

# Fight routes
@api.route('/fights', methods=['GET'])
def get_fights():
    fights = Fight.query.all()
    return jsonify([fight.to_dict() for fight in fights])

@api.route('/fights/<int:id>', methods=['GET'])
def get_fight(id):
    fight = Fight.query.get_or_404(id)
    return jsonify(fight.to_dict())

@api.route('/fights', methods=['POST'])
def create_fight():
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400
    
    data = request.json
    
    # Validate required fields
    if 'event_id' not in data:
        return jsonify({'error': 'Missing event_id'}), 400
    
    # Validate event exists
    event = Event.query.get(data['event_id'])
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    # Validate fighters exist if provided
    if 'fighter1_id' in data:
        fighter1 = Fighter.query.get(data['fighter1_id'])
        if not fighter1:
            return jsonify({'error': 'Fighter 1 not found'}), 404
    
    if 'fighter2_id' in data:
        fighter2 = Fighter.query.get(data['fighter2_id'])
        if not fighter2:
            return jsonify({'error': 'Fighter 2 not found'}), 404
    
    fight = Fight(
        event_id=data['event_id'],
        fighter1_id=data.get('fighter1_id'),
        fighter2_id=data.get('fighter2_id'),
        weight_class=data.get('weight_class'),
        scheduled_rounds=data.get('scheduled_rounds', 3)
    )
    
    try:
        db.session.add(fight)
        db.session.commit()
        return jsonify(fight.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Could not create fight'}), 400

@api.route('/fights/<int:id>', methods=['PUT'])
def update_fight(id):
    fight = Fight.query.get_or_404(id)
    
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400
    
    data = request.json
    
    # Validate event exists if provided
    if 'event_id' in data:
        event = Event.query.get(data['event_id'])
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        fight.event_id = data['event_id']
    
    # Validate fighters exist if provided
    if 'fighter1_id' in data:
        if data['fighter1_id'] is not None:  # Allow setting to NULL
            fighter1 = Fighter.query.get(data['fighter1_id'])
            if not fighter1:
                return jsonify({'error': 'Fighter 1 not found'}), 404
        fight.fighter1_id = data['fighter1_id']
    
    if 'fighter2_id' in data:
        if data['fighter2_id'] is not None:  # Allow setting to NULL
            fighter2 = Fighter.query.get(data['fighter2_id'])
            if not fighter2:
                return jsonify({'error': 'Fighter 2 not found'}), 404
        fight.fighter2_id = data['fighter2_id']
    
    # Update other fields
    if 'weight_class' in data:
        fight.weight_class = data['weight_class']
    if 'scheduled_rounds' in data:
        fight.scheduled_rounds = data['scheduled_rounds']
    
    try:
        db.session.commit()
        return jsonify(fight.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Could not update fight'}), 400

@api.route('/fights/<int:id>', methods=['DELETE'])
def delete_fight(id):
    fight = Fight.query.get_or_404(id)
    
    try:
        db.session.delete(fight)
        db.session.commit()
        return jsonify({'result': True})
    except:
        db.session.rollback()
        return jsonify({'error': 'Could not delete fight'}), 400 