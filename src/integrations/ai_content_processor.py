"""
AI Content Processor for Pipedream

This module processes and combines outputs from Claude and ChatGPT AI models,
converting their markdown content to HTML with proper formatting. It handles
error cases, demotes headings, and provides a formatted date for the output.

The main handler function expects a Pipedream context object and returns a
dictionary containing the processed HTML body and formatted date.
"""

import markdown
import datetime
from src.utils.content_processing import get_content_from_path, demote_headings

def handler(pd: "pipedream"):
    """
    Main handler function for processing AI content in Pipedream.
    
    Args:
        pd (pipedream): The Pipedream context object
        
    Returns:
        dict: A dictionary containing:
            - html_body (str): The combined HTML output
            - formatted_date (str): Today's date in a formatted string
    """
    # --- 1. Get Markdown Content from Previous Steps ---
    claude_markdown_content = ""
    chatgpt_markdown_content = ""
    error_messages = []

    # Path for Claude's output
    claude_path = ["chat1", "$return_value", "content", 0, "text"]
    fetched_claude_content = get_content_from_path(pd.steps, claude_path, "chat1")
    if fetched_claude_content is None: 
        error_messages.append("<!-- Error fetching Claude's content. Check Pipedream logs for step 'chat1'. -->")
        claude_markdown_content = "" 
    else:
        claude_markdown_content = fetched_claude_content
    print(f"Received Claude's Markdown Content (first 100 chars): {claude_markdown_content[:100]}...")

    # Path for ChatGPT's output
    chatgpt_path = ["chat", "$return_value", "generated_message", "content"]
    fetched_chatgpt_content = get_content_from_path(pd.steps, chatgpt_path, "chat")
    if fetched_chatgpt_content is None: 
        error_messages.append("<!-- Error fetching ChatGPT's content. Check Pipedream logs for step 'chat'. -->")
        chatgpt_markdown_content = "" 
    else:
        chatgpt_markdown_content = fetched_chatgpt_content
    print(f"Received ChatGPT's Markdown Content (first 100 chars): {chatgpt_markdown_content[:100]}...")

    # --- 2. Convert Markdown to HTML and Demote Headings ---
    claude_html_output = ""
    chatgpt_html_output = ""

    try:
        if claude_markdown_content:
            print("Converting Claude's Markdown to HTML...")
            initial_claude_html = markdown.markdown(claude_markdown_content)
            print("Demoting headings in Claude's HTML...")
            claude_html_output = demote_headings(initial_claude_html)
            print("Claude's HTML processing successful.")
        else:
            print("No Claude Markdown content to process.")
            claude_html_output = "<p><em>(No content from Claude)</em></p>"

        if chatgpt_markdown_content:
            print("Converting ChatGPT's Markdown to HTML...")
            initial_chatgpt_html = markdown.markdown(chatgpt_markdown_content)
            print("Demoting headings in ChatGPT's HTML...")
            chatgpt_html_output = demote_headings(initial_chatgpt_html)
            print("ChatGPT's HTML processing successful.")
        else:
            print("No ChatGPT Markdown content to process.")
            chatgpt_html_output = "<p><em>(No content from ChatGPT)</em></p>"

    except Exception as e:
        print(f"Error during Markdown to HTML conversion or heading demotion: {e}")
        error_messages.append(f"<!-- Error during HTML processing: {e} -->")
        claude_html_output = claude_html_output or ""
        chatgpt_html_output = chatgpt_html_output or ""

    # --- 3. Combine HTML Outputs with Headers and Separator ---
    combined_html_body = ""
    if error_messages:
        combined_html_body += "\n".join(error_messages) + "\n<hr style=\"margin-top:1em; margin-bottom:1em;\">\n"

    if claude_html_output:
        combined_html_body += "<h1>Claude's Output</h1>\n"
        combined_html_body += claude_html_output
        combined_html_body += "\n" 

    if claude_html_output and chatgpt_html_output:
        combined_html_body += "<hr style=\"margin-top:1em; margin-bottom:1em;\">\n"

    if chatgpt_html_output:
        combined_html_body += "<h1>ChatGPT's Output</h1>\n"
        combined_html_body += chatgpt_html_output
        combined_html_body += "\n" 
    
    if not combined_html_body.strip():
        combined_html_body = "<p><em>(No content from either AI source to display.)</em></p>"

    # --- 4. Get and Format Today's Date ---
    try:
        today = datetime.date.today()
        day_str = str(today.day)
        formatted_date = today.strftime(f"%B {day_str}, %Y")
        print(f"Formatted date: {formatted_date}")
    except Exception as e:
        print(f"Error formatting date: {e}")
        formatted_date = "Date unavailable"

    # --- 5. Return Combined HTML Output and Formatted Date ---
    return {
        "html_body": combined_html_body,
        "formatted_date": formatted_date
    } 