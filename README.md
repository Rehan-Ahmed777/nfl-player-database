# NFL Player Database Aggregator

A web application that provides a comprehensive, refreshable NFL player database aggregating data from multiple sources including the Sleeper API and various NFL statistics websites.

## Features

- **One-Click Refresh**: Update all player data in real-time with a single click
- **Multi-Source Data**: Aggregates information from:
  - Sleeper API (player info, rosters)
  - Fantasy Pros (dynasty rankings)
  - RAS Football (athletic scores)
  - Over The Cap (free agency information)
  - Football DB (draft information)
  
- **Fantasy League Integration**: 
  - Track player ownership across multiple Sleeper leagues
  - See which players you own, which are available, and who owns them
  
- **Comprehensive Filtering**:
  - Filter by position (QB, RB, WR, TE)
  - Filter by team
  - Search by player name
  - Real-time filter updates

- **Rich Player Data**:
  - Name, Position, Team
  - Experience, Height, Weight
  - College, Age, Birthdate
  - Dynasty Rankings (Overall & Position)
  - RAS Score
  - Free Agency Status & Year
  - Draft Information (Year, Round, Pick)
  - League Ownership Status

## Installation

1. Install Python 3.8 or higher

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

1. **Enter Your Sleeper Username**: Input your Sleeper fantasy football username
2. **Add League IDs**: Enter one or more Sleeper league IDs (you can find these in your league URL)
3. **Click "Load Player Data"**: The system will fetch and aggregate all data (this may take 1-2 minutes)
4. **View & Filter**: Use the filters to narrow down players or search by name
5. **Refresh**: Click "Load Player Data" again anytime to refresh all information

## Technical Details

### Backend (Python/Flask)
- Fetches player data from Sleeper API
- Web scraping using BeautifulSoup and Selenium
- Data matching and aggregation
- RESTful API endpoint

### Frontend (HTML/CSS/JavaScript)
- Responsive design
- Dynamic table generation
- Real-time filtering
- Modern UI with Font Awesome icons

## Data Sources

1. **Sleeper API**: Base player information and roster data
2. **Fantasy Pros**: Dynasty rankings
3. **RAS Football**: Relative Athletic Scores
4. **Over The Cap**: Free agency information
5. **Football DB**: NFL draft history

## Notes

- Players are filtered to only include QB, RB, WR, and TE positions
- Age cap of 45 years old is applied
- Some websites may have anti-scraping measures that could affect data availability
- The application runs locally and is private by default

## Deployment

For production deployment on Netlify or similar platforms:

1. Configure the Flask app for production
2. Set up environment variables
3. Use a production WSGI server (gunicorn)
4. Configure HTTPS and security settings

## Future Enhancements

- Add more data sources
- Implement caching for faster load times
- Add export functionality (CSV, Excel)
- Player comparison features
- Historical data tracking

## License

This project is for personal use. Respect the terms of service of all data sources.
