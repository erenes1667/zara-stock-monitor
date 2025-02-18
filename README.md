# Zara Stock Monitor

An advanced stock monitoring tool for Zara products with Discord notifications and screenshot capabilities.

## Features

- 🔍 Monitors multiple products simultaneously
- 📏 Checks for specific sizes
- 📷 Takes screenshots of available products
- 💬 Sends notifications via Discord
- 🤖 Advanced anti-bot detection measures
- ⏰ Configurable check intervals
- 📝 Detailed logging
- 💰 Price tracking
- 🔄 Automatic retry on errors

## Setup

1. Create a Discord webhook:
   - Open your Discord server settings
   - Go to Integrations > Webhooks
   - Create a new webhook
   - Copy the webhook URL

2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the tool:
   - Copy `config.json` and update with your:
     - Product URLs
     - Desired sizes
     - Discord webhook URL
     - Check intervals

## Configuration

Example config.json:
```json
{
    "products": [
        {
            "url": "https://www.zara.com/your-product-url",
            "sizes": ["XS", "S", "M", "L", "XL"],
            "name": "Example Product Name",
            "price": null
        }
    ],
    "discord_webhook_url": "YOUR_DISCORD_WEBHOOK_URL",
    "check_interval_min": 300,
    "check_interval_max": 600
}
```

## Usage

Run the script:
```bash
python stock_monitor.py
```

The tool will:
- Monitor specified products
- Take screenshots when stock is found
- Send Discord notifications with:
  - Available sizes
  - Product price
  - Screenshot
  - Direct link to product
- Log all activities
- Clean up old screenshots automatically

## Discord Notifications

Each notification includes:
- Product name
- Available sizes
- Current price
- Last check time
- Direct link to product
- Screenshot of size selector showing availability

## Improvements Over Original

1. Better Architecture:
   - Used dataclasses for type safety
   - Implemented proper logging
   - Added type hints
   - More modular code structure

2. Enhanced Security:
   - Using undetected-chromedriver
   - Random user agents
   - Dynamic delays
   - Headless mode support

3. New Features:
   - Screenshot capabilities
   - Price tracking
   - Last check timestamps
   - Rich Discord embeds
   - Automatic screenshot cleanup

4. Better Error Handling:
   - Comprehensive exception handling
   - Automatic retries
   - Detailed logging
   - Resource cleanup

## Logs

The tool maintains detailed logs in `stock_monitor.log` including:
- Stock checks
- Found availability
- Errors
- Notifications sent
- Screenshot operations

## Screenshots

Screenshots are saved in the `screenshots` directory and are automatically cleaned up after being sent to Discord to save space.

## Contributing

Feel free to submit issues and enhancement requests!