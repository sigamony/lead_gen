# Google Maps Scraper with WhatsApp Automation

A powerful Streamlit web application that combines Google Maps business data scraping with automated WhatsApp messaging capabilities. This tool helps businesses and marketers find potential leads and engage with them through WhatsApp.

## 🌟 Features

- **Google Maps Scraping**
  - Search for businesses based on location and type
  - Extract business details including:
    - Business name
    - Address
    - Phone numbers
    - Website
    - Reviews and ratings
  - Export data to Excel/CSV formats

- **WhatsApp Automation**
  - Send messages to multiple contacts
  - Support for bulk messaging
  - Automatic phone number formatting
  - Message delivery status tracking
  - Rate limiting to prevent blocking
  - Instant messaging support
  - Automatic browser tab management

- **AI-Powered Interface**
  - Natural language processing for search queries using Google's Gemini AI
  - Smart message preparation
  - Intelligent lead selection
  - User-friendly Streamlit interface
  - Context-aware business search interpretation
  - Automated query optimization

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- WhatsApp Web/Desktop installed and logged in
- Google API Key (for Gemini AI features)
- Modern web browser (Chrome recommended)
- Stable internet connection


## 💡 Usage

### Searching for Businesses

1. Enter your search query in natural language (e.g., "Find cafes in Islamabad")
2. Specify the number of results you want
3. View the results in the interactive table
4. Download the data in Excel or CSV format

### Sending WhatsApp Messages

1. Prepare your message content
2. Choose recipients:
   - Direct phone numbers
   - Results from a search
   - Specific number of leads from search results
3. Ensure WhatsApp Web is open and logged in
4. Send messages and monitor delivery status

### Natural Language Processing

The application uses Google's Gemini AI to understand and process natural language queries. Examples:

- "Find me graphic design clients in New York"
- "Look for companies needing marketing services in London"
- "Get me plumbing leads in Chicago"
- "Find cafes in Islamabad and send them a promotional message"

## ⚙️ Configuration

The application can be configured through various parameters:

- `MESSAGE_INTERVAL`: Delay between messages (default: 15 seconds)
- `PYWHATKIT_WAIT_TIME`: Wait time for WhatsApp Web (default: 25 seconds)
- `MAX_RETRIES`: Maximum retry attempts for failed messages
- `DEFAULT_COUNTRY_CODE`: Default country code for phone numbers
- `GEMINI_MODEL`: AI model version (default: gemini-1.5-flash-latest)

## 🔒 Security and Privacy

- API keys are stored in environment variables
- Phone numbers are validated and formatted securely
- Rate limiting prevents abuse
- No data is stored permanently
- Secure handling of WhatsApp credentials
- Automatic browser session cleanup

## 🛠️ Technical Details

### Key Technologies

- **Streamlit**: Web interface
- **Playwright**: Browser automation
- **Pandas**: Data handling
- **Google Gemini AI**: Natural language processing
- **PyWhatKit**: WhatsApp automation
- **Python-dotenv**: Environment management


## ⚠️ Important Notes

- Always ensure WhatsApp Web is open and logged in before sending messages
- Respect WhatsApp's terms of service and rate limits
- Use the tool responsibly and ethically
- Keep your API keys secure
- Monitor your Google API usage to stay within limits
- Regular updates to Playwright browsers may be required

