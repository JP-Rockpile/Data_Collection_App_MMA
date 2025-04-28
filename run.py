from app import create_app
import click

app = create_app()

@app.cli.command('scrape')
@click.option('--start-url', required=True, help='URL to start scraping from')
def scrape_command(start_url):
    """Run the scraper starting from the given URL."""
    from app.scraper import main_scraper
    click.echo(f'Starting scraper at: {start_url}')
    main_scraper(start_url)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 