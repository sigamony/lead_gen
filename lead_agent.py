import streamlit as st
import pandas as pd
import asyncio
import playwright.async_api
from playwright.async_api import async_playwright
import os
import logging
from dataclasses import dataclass, asdict, field
import datetime
import time
import google.generativeai as genai
from dotenv import load_dotenv
import json
import pywhatkit

# Load environment variables
load_dotenv()
API_KEY = os.getenv('GOOGLE_API_KEY')

if not API_KEY:
    st.error("Error: GOOGLE_API_KEY not found in environment variables.")
    st.stop()

genai.configure(api_key=API_KEY)

# --- Define Tool Schemas (Functions the LLM can 'call') ---
search_Maps_func = {
    "name": "search_Maps",
    "description": "Searches Google Maps for businesses based on a query.",
    "parameters": {
        # Use UPPERCASE type names
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING", # Use UPPERCASE
                "description": "The search term for Google Maps (e.g., 'cafes in islamabad', 'restaurants near Eiffel Tower'). Include the type of place and location.",
            },
            "num_results": {
                "type": "INTEGER", # Use UPPERCASE
                "description": "Optional. The desired approximate number of business results to find. Defaults to 20 if not specified.",
            },
        },
        "required": ["query"],
    },
}

prepare_whatsapp_message_func = {
    "name": "prepare_whatsapp_message",
    "description": "Prepares the content and specifies the number of recipients for a WhatsApp message campaign.",
    "parameters": {
        # Use UPPERCASE type names
        "type": "OBJECT",
        "properties": {
            "message": {
                "type": "STRING", # Use UPPERCASE
                "description": "The exact content of the WhatsApp message to be sent.",
            },
            "k": {
                "type": "INTEGER", # Use UPPERCASE
                "description": "Optional. The maximum number of recipients (leads) from the search results to send the message to.",
            },
            "target_numbers": {
                "type": "ARRAY", # Use UPPERCASE
                # The 'items' schema still defines the type of elements within the array
                "items": {"type": "STRING"}, # Keep nested type as STRING
                "description": "Optional. A specific list of phone numbers to send the message to.",
            }
        },
        "required": ["message"],
    },
}

# Initialize the LLM Model with the corrected Tools
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    tools=[search_Maps_func, prepare_whatsapp_message_func] # Pass the corrected dictionaries
)


asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# # Ensure necessary system packages are installed
# os.system(
#     'apt-get update && apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxfixes3 libxi6 libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libpango-1.0-0 libgdk-pixbuf2.0-0 libgtk-3-0 libdrm2'
# )

# # Install Playwright
# os.system('pip install playwright')

# # Install Playwright browsers
# os.system('playwright install')


# Ensure Playwright browsers are installed
async def install_playwright_browsers():
    from playwright.__main__ import main as playwright_main
    await asyncio.create_task(playwright_main(['install']))


# asyncio.run(install_playwright_browsers())


# Ensuring Playwright browsers are installed
async def install_playwright_browsers():
    from playwright.__main__ import main as playwright_main
    await asyncio.create_task(playwright_main(['install']))


# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


@dataclass
class Business:
    """Holds business data"""
    name: str = None
    address: str = None
    website: str = None
    phone_number: str = None
    # reviews_count: int = None
    reviews_average: float = None

    def __eq__(self, other):
        if not isinstance(other, Business):
            return NotImplemented
        return (self.name, self.address, self.website, self.phone_number,
                self.reviews_average) == \
               (other.name, other.address, other.website, other.phone_number,
                 other.reviews_average)

    def __hash__(self):
        return hash((self.name, self.address, self.website, self.phone_number,
                     self.reviews_average))


@dataclass
class BusinessList:
    """Holds list of Business objects, and saves to both Excel and CSV"""
    business_list: list[Business] = field(default_factory=list)
    save_at = 'output'

    def dataframe(self):
        """Transform business_list to pandas DataFrame"""
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_")

    def save_to_excel(self, filename):
        """Saves pandas DataFrame to Excel (xlsx) file and returns file path"""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        file_path = f"{self.save_at}/{filename}.xlsx"
        try:
            self.dataframe().to_excel(file_path, index=False)
            logging.info(f"Saved data to {file_path}")
            return file_path  # Return the file path after saving
        except Exception as e:
            logging.error(f"Failed to save data to Excel: {e}")
            return None

    def save_to_csv(self, filename):
        """Saves pandas DataFrame to CSV file"""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        file_path = f"{self.save_at}/{filename}.csv"
        try:
            self.dataframe().to_csv(file_path, index=False)
            logging.info(f"Saved data to {file_path}")
        except Exception as e:
            logging.error(f"Failed to save data to CSV: {e}")

    def get_row_size(self):
        """Returns the number of rows in the DataFrame"""
        return len(self.business_list)


async def scrape_business(search_term, total):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("https://www.google.com/maps", timeout=60000)
            await page.wait_for_timeout(5000)

            await page.fill('//input[@id="searchboxinput"]', search_term)
            await page.wait_for_timeout(3000)

            await page.keyboard.press("Enter")
            await page.wait_for_timeout(5000)

            await page.hover(
                '//a[contains(@href, "https://www.google.com/maps/place")]')

            previously_counted = 0
            listings = []

            while True:
                await page.mouse.wheel(0, 10000)
                await page.wait_for_timeout(2000)

                current_count = await page.locator(
                    '//a[contains(@href, "https://www.google.com/maps/place")]'
                ).count()
                if current_count >= total:

                    all_listings = await page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).all()

                    listings = all_listings[:total]

                    break

                elif current_count == previously_counted:

                    listings = await page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).all()

                    break

                else:
                    previously_counted = current_count

            business_list = BusinessList()

            for listing in listings:
                try:
                    await listing.click()
                    await page.wait_for_timeout(3000)

                    name_css_selector = 'h1.DUwDvf.lfPIob'
                    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                    website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
                    phone_number_xpath = '//button[contains(@data-item-id, "phone")]//div[contains(@class, "fontBodyMedium")]'
                    # review_count_xpath = '//button[@jsaction="pane.reviewChart.moreReviews"]//span'
                    reviews_average_xpath = '//div[@jsaction="pane.reviewChart.moreReviews"]//div[@role="img"]'

                    business = Business()

                    if await page.locator(name_css_selector).count() > 0:
                        business.name = await page.locator(name_css_selector
                                                           ).inner_text()
                    else:
                        business.name = ""

                    if await page.locator(address_xpath).count() > 0:
                        address_elements = await page.locator(address_xpath
                                                              ).all()
                        if address_elements:
                            business.address = await address_elements[
                                0].inner_text()
                        else:
                            business.address = ""
                    else:
                        business.address = ""

                    if await page.locator(website_xpath).count() > 0:
                        website_elements = await page.locator(website_xpath
                                                              ).all()
                        if website_elements:
                            business.website = await website_elements[
                                0].inner_text()
                        else:
                            business.website = ""
                    else:
                        business.website = ""

                    if await page.locator(phone_number_xpath).count() > 0:
                        phone_elements = await page.locator(phone_number_xpath
                                                            ).all()
                        if phone_elements:
                            business.phone_number = await phone_elements[
                                0].inner_text()
                        else:
                            business.phone_number = ""
                    else:
                        business.phone_number = ""

                    # if await page.locator(review_count_xpath).count() > 0:
                    #     review_count_text = await page.locator(
                    #         review_count_xpath).inner_text()
                    #     business.reviews_count = int(
                    #         review_count_text.split()[0].replace(',',
                    #                                              '').strip())
                    # else:
                    #     business.reviews_count = None

                    if await page.locator(reviews_average_xpath).count() > 0:
                        reviews_average_text = await page.locator(
                            reviews_average_xpath).get_attribute('aria-label')
                        if reviews_average_text:
                            business.reviews_average = float(
                                reviews_average_text.split()[0].replace(
                                    ',', '.').strip())
                        else:
                            business.reviews_average = None
                    else:
                        business.reviews_average = None

                    business_list.business_list.append(business)
                except Exception as e:
                    logging.error(
                        f'Error occurred while scraping listing: {e}')

            await browser.close()
            return business_list

        except Exception as e:
            logging.error(f'Error occurred during scraping: {e}')
            await browser.close()
            return BusinessList()

async def get_agent_plan(user_input: str):
    """
    Processes user input using the LLM to determine intent and extract parameters.
    Handles both function calls and text responses safely. Interprets indirect queries.
    """
    planned_calls = []
    llm_text_output = ""  # To store any textual response from the LLM

    try:
        chat = model.start_chat()
        # --- Updated Prompt ---
        prompt = f"""Analyze the following user request for lead generation using the available tools: 'search_Maps' and 'prepare_whatsapp_message'.

        **CRITICAL TASK:** Interpret the user's request to identify the **type of business or place** they are actually looking for on Google Maps, especially when they use terms like 'clients' or 'leads'. Formulate the most effective search query for the 'search_Maps' tool.

        **Interpretation Examples:**
        - User: "find me graphic design clients in New York" -> Your interpretation: The user wants businesses that *are* graphic designers or *hire* them. -> **Search Query:** "graphic designers in New York" OR "graphic design agency in New York"
        - User: "look for companies needing marketing services in London" -> Your interpretation: The user wants potential clients for marketing. -> **Search Query:** "marketing agency in London" OR "businesses in London" (less specific, might need clarification)
        - User: "get me plumbing leads in Chicago" -> Your interpretation: The user wants plumbing businesses. -> **Search Query:** "plumbers in Chicago" OR "plumbing companies in Chicago"
        - User: "find cafes in Islamabad and send message X" -> Your interpretation: Direct request. -> **Search Query:** "cafes in Islamabad"

        **User Request:** "{user_input}"

        **Your Steps:**
        1.  Carefully analyze the User Request.
        2.  Determine the core action(s): Search Maps, Prepare WhatsApp message, or Both.
        3.  **If searching:** Formulate the best possible `query` string for Google Maps based on your interpretation (as shown in examples) and identify the `location`. Determine `num_results` (default 20 if unspecified).
        4.  **If messaging:** Extract the `message` content, the limit `k`, or specific `target_numbers`.
        5.  Identify the correct function(s) ('search_Maps', 'prepare_whatsapp_message') to call and construct their arguments precisely.
        6.  If the plan involves searching and then messaging those results, ensure 'search_Maps' is called first.
        """
        # --- End of Updated Prompt ---

        response = chat.send_message(prompt)

        # (Rest of the function to parse response remains the same...)
        # Iterate through the parts of the response candidate
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                # --- Check for Function Call FIRST ---
                if part.function_call:
                    call = part.function_call
                    function_name = call.name
                    args = {key: value for key, value in call.args.items()} if hasattr(call, 'args') else {}

                    if function_name == "search_Maps" and "num_results" not in args:
                        args["num_results"] = 20

                    planned_calls.append({
                        "function_name": function_name,
                        "args": args
                    })
                # --- If not a function call, check for text ---
                elif hasattr(part, 'text'):
                    llm_text_output += part.text + "\n"

        if not planned_calls and not llm_text_output:
            try:
                llm_text_output = response.text
            except ValueError as ve:
                llm_text_output = f"LLM response contained a function call but no text. ({ve})"
            except Exception as text_exc:
                 llm_text_output = f"Could not extract text response: {text_exc}"

    except Exception as e:
        error_message = f"An error occurred during LLM interaction: {type(e).__name__} - {str(e)}"
        st.error(error_message)
        return [], error_message

    return planned_calls, llm_text_output.strip()


async def main():
    st.title("AI-Powered Lead Generation Assistant")

    st.text("By Jeremy Sigamony") 
    st.markdown("---")

    st.markdown(
        """
    <p style="font-size: 13px;color: aqua;">Enter your request in natural language. Examples:</p>
    <ul>
        <li>"Find cafes in Islamabad and send the first 5 this message: 'Hello! We have a special offer today.'"</li>
        <li>"Show me barber shops in Malakand, maybe 10 of them."</li>
        <li>"Send 'Meeting reminder for tomorrow at 10 AM' to +923001234567 and +923339876543"</li>
    </ul>
    """,
        unsafe_allow_html=True,
    )

    user_input = st.text_area(
        "Enter your request",
        placeholder="e.g., Find cafes in Islamabad and send them a promotional message"
    )


    if st.button("Process Request"):
        if not user_input:
            st.error("Please enter your request")
        else:
            with st.spinner("Analyzing your request..."):
                planned_calls, llm_response = await get_agent_plan(user_input)

                if planned_calls:
                    st.success("Request analyzed successfully!")
                    st.json(planned_calls) # Show the plan

                    # --- Store results temporarily if needed for later steps ---
                    search_results_list = None

                    # Process each planned call
                    for call in planned_calls:
                        if call["function_name"] == "search_Maps":
                            with st.spinner("Searching Google Maps..."):
                                # --- Get and VALIDATE num_results ---
                                num_results_arg = call["args"].get("num_results", 20) # Default to 20
                                try:
                                    # Convert to integer
                                    num_results_int = int(num_results_arg)
                                    if num_results_int <= 0: # Add check for non-positive
                                        st.warning(f"Number of results must be positive ('{num_results_arg}' received). Defaulting to 20.")
                                        num_results_int = 5
                                except (ValueError, TypeError):
                                    st.warning(f"Invalid value received for number of results ('{num_results_arg}'). Defaulting to 20.")
                                    num_results_int = 20
                                # --- End Validation ---

                                # Pass the validated integer to the scraper
                                business_list = await scrape_business(
                                    call["args"]["query"],
                                    num_results_int # Use the integer value
                                )
                                search_results_list = business_list # Store for potential later use

                                if business_list and business_list.business_list: # Check if list is not None and not empty
                                    st.success(f"Found {len(business_list.business_list)} results!")
                                    st.dataframe(business_list.dataframe())

                                    # Save results
                                    current_datetime = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                    search_for_filename = call["args"]["query"].replace(' ', '_').replace('/','_') # Basic sanitization
                                    excel_filename = f"({len(business_list.business_list)}_Rows)__{current_datetime}__({search_for_filename})"

                                    excel_file_path = business_list.save_to_excel(excel_filename)
                                    if excel_file_path:
                                        try:
                                            with open(excel_file_path, 'rb') as fp:
                                                st.download_button(
                                                    label="Download Results (Excel)",
                                                    data=fp,
                                                    file_name=f"{excel_filename}.xlsx",
                                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" # Correct MIME type
                                                )
                                        except FileNotFoundError:
                                             st.error(f"Could not read file for download: {excel_file_path}")
                                    else:
                                         st.error("Failed to save results to Excel.")
                                else:
                                     st.warning("No results found or scraping failed.")


                        elif call["function_name"] == "prepare_whatsapp_message":
                            st.info("WhatsApp Message Action:")
                            message_content = call['args'].get('message', '*No message content provided*')
                            k_value = call['args'].get('k')
                            target_numbers = call['args'].get('target_numbers')

                            st.write(f"**Message:** {message_content}")

                            # Handle direct target numbers if provided
                            if target_numbers:
                                st.write("**Target numbers (direct):**", target_numbers)
                                with st.spinner("Sending messages to direct numbers..."):
                                    for number in target_numbers:
                                        if await send_whatsapp_message(number, message_content):
                                            st.success(f"Message sent to {number}")
                                        else:
                                            st.error(f"Failed to send message to {number}")

                            # Handle search results if available
                            elif search_results_list and search_results_list.business_list:
                                if k_value is not None:
                                    try:
                                        k_int = int(k_value)
                                        st.write(f"**Number of recipients (k):** {k_int}")
                                        
                                        # Get phone numbers from search results
                                        phone_numbers = [
                                            business.phone_number 
                                            for business in search_results_list.business_list[:k_int]
                                            if business.phone_number  # Only include if phone number exists
                                        ]
                                        
                                        if not phone_numbers:
                                            st.warning("No valid phone numbers found in the search results.")
                                        else:
                                            with st.spinner(f"Sending messages to {len(phone_numbers)} recipients..."):
                                                for number in phone_numbers:
                                                    if await send_whatsapp_message(number, message_content):
                                                        st.success(f"Message sent to {number}")
                                                    else:
                                                        st.error(f"Failed to send message to {number}")
                                        
                                    except (ValueError, TypeError):
                                        st.warning(f"Invalid value received for k ('{k_value}')")
                                else:
                                    st.warning("No 'k' value provided to limit the number of recipients.")
                            else:
                                st.warning("No search results available to send messages to.")


                else: # No planned calls from LLM
                    st.info("LLM Response:")
                    st.write(llm_response if llm_response else "No specific action identified by the AI.")


async def send_whatsapp_message(phone_number: str, message: str, wait_time: int = 25) -> bool:
    """
    Sends a WhatsApp message using pywhatkit.
    
    Args:
        phone_number: The target phone number in international format (e.g., +923348958772)
        message: The message content to send
        wait_time: How long to wait for WhatsApp Web to load (default: 25 seconds)
    
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        logging.info(f"Attempting to send WhatsApp message to: {phone_number}")
        logging.info(f"Message: {message}")
        logging.info(f"Waiting {wait_time} seconds for WhatsApp Web/Desktop...")
        
        pywhatkit.sendwhatmsg_instantly(
            phone_no=phone_number,
            message=message,
            wait_time=wait_time,
            tab_close=True,
            close_time=3
        )
        
        logging.info("Message sent successfully!")
        return True
        
    except Exception as e:
        error_type = type(e).__name__
        logging.error(f"An error occurred: {error_type} - {e}")
        st.error(f"Failed to send message to {phone_number}. Error: {error_type}")
        return False


if __name__ == "__main__":
    asyncio.run(main())
