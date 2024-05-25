from email.mime.text import MIMEText
import os
import smtplib
import time
import random
import argparse

import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Read prompts from text file, one line each time, put them in an array, and print them out
# Open the file
with open("mars_prompts.txt", "r") as file:
    # Read lines into a list
    prompts = file.readlines()
    # Remove the newline character from each line
    prompts = [prompt.strip() for prompt in prompts]

# Read fake ids from a file
with open("fakeid.txt", "r") as file:
    fake_ids = file.readlines()
    # Remove the newline character from each line
    fake_ids = [fake_id.strip() for fake_id in fake_ids]

# Setup cookie
cookie = "p_h5_upload_u=F4A75158-C3ED-423A-A55E-AE3F23566730; SESSION=8ec92b4b-6406-459c-b7d2-6f75fd800354; __utma=259938259.798573350.1713161719.1714457659.1714976241.4; __utmz=259938259.1713161719.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); Hm_lvt_5f84ed9f466f8dbb7c6e59266e1a74b8=1713161718,1713578567,1714457658"

# Setup app angent
app_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 12_5_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 version/cshdAPP appName/eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJuYmYiOjE3MTM0OTE2NjgsImV4cCI6MTcxNjA4MzY2OCwiaWF0IjoxNzEzNDkxNjY4LCJ1c2VySWQiOjQ4NDIwOH0.531v3I9iIfDkndLXrvb5VwSCiyXmGe_Ili1yfuUZQ2U ticket/484208 userid"

# Setup api of text-to-image
api_prefix = "https://web2.kbw.hbjt.com.cn/image/about/"

# Endpoint of text-to-image
api_text_to_image = api_prefix + "inText"

# Endpoint of get ai image
api_get_ai_image = api_prefix + "getAiImg"

# Endpoint of translate
api_translate = "https://chengshi.dskb.cn/api/translate"


def send_email(recipient_email, subject, message):
    """Sends a warning email using SMTP."""
    try:
        # Replace with your email server details
        smtp_server = os.getenv(
            "SMTP_SERVER"
        )  # Get SMTP server from environment variable
        smtp_port = int(
            os.getenv("SMTP_PORT")
        )  # Get SMTP port from environment variable
        sender_email = os.getenv(
            "SENDER_EMAIL"
        )  # Get sender email from environment variable
        sender_password = os.getenv(
            "SENDER_PASSWORD"
        )  # Get sender password from environment

        # Validate that all required environment variables are set
        if not all([smtp_server, smtp_port, sender_email, sender_password]):
            raise ValueError(
                "Missing environment variables. Please check your .env file."
            )

        # Create a secure connection with the server
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Enable TLS encryption
            server.login(sender_email, sender_password)

            # Create and send the email
            msg = MIMEText(message)
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = recipient_email
            server.sendmail(sender_email, recipient_email, msg.as_string())
            print("Warning email sent successfully.")

    except Exception as e:
        print(f"Error sending warning email: {e}")


def main():
    """
    Reads two integer arguments from the command line using argparse.
    """
    parser = argparse.ArgumentParser(
        description="Reads two integer arguments for your application."
    )
    parser.add_argument(
        "--prompt_start", type=int, required=True, help="Starting value for prompts"
    )
    args = parser.parse_args()

    # Slice prompts and fake_ids based on the arguments
    # prompts lenght is 800
    # fake_ids length is 500
    prompts_slice = prompts[args.prompt_start : args.prompt_start + 800]

    # Retry parameters
    max_retries = 3  # Maximum number of retries
    retry_delay = 2  # Delay (in seconds) between retries

    # Recipient email
    recipient_email = "madfxgao@gmail.com"

    # Loop through fake_ids and need index
    for prompt in prompts_slice:
        # Send request to translate api
        print(f"Translate: {prompt} to English")
        for attempt in range(max_retries + 1):
            try:
                with httpx.Client() as client:
                    params = {
                        "sourceText": prompt,
                        "formatType": "text",
                        "sourceLanguage": "auto",
                        "scene": "general",
                        "targetLanguage": "en",
                    }
                    response = client.post(api_translate, json=params)
                    response.raise_for_status()  # Raise an exception for HTTP errors
                    prompt_translated = response.json()["data"]["translated"]
                    print("Translate API Response:", prompt_translated)
                    break

            except Exception as exc:
                print(f"Error (Attempt {attempt + 1}): {exc}")
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    send_email(
                        recipient_email,
                        "API Request Failure",
                        f"API request to {api_translate} failed. Retrying in {retry_delay} seconds...",
                    )
                    time.sleep(retry_delay)
                else:
                    print("Maximum retries reached. Giving up.")
                    send_email(
                        recipient_email,
                        "API Request Failure",
                        f"API request to {api_translate} failed after {max_retries} attempts.",
                    )

        # Send request to text-to-image api
        print(f"Send request to text-to-image api with prompt: {prompt_translated}")
        try:
            with httpx.Client() as client:
                response = client.post(
                    api_text_to_image,
                    headers={"user-agent": app_agent},
                    json={"des": prompt_translated},
                )
                response.raise_for_status()  # Raise an exception for HTTP errors
                job_id = response.json()["data"]
                print("Text-to-Image API Response:", job_id)
        except httpx.HTTPStatusError as exc:
            print(f"Error: {exc}")

        # Send request to get ai image, interval is 5 second until the response return a success status
        print(f"Send request to get ai image with job_id: {job_id}")
        while True:
            try:
                with httpx.Client() as client:
                    response = client.post(
                        api_get_ai_image,
                        headers={"user-agent": app_agent},
                        json={"requestId": job_id},
                    )
                    response.raise_for_status()  # Raise an exception for HTTP errors
                    response_json = response.json()
                    if response_json["code"] == "1000":
                        ai_image_url = response_json["data"]
                        print("Get AI Image API Response:", ai_image_url)
                        break
                    time.sleep(5)
            except httpx.HTTPStatusError as exc:
                print(f"Error: {exc}")

        # Send request to create a post
        fake_id = fake_ids[random.randint(0, 1053)]
        print(f"Send request to create a post with fake_id: {fake_id}")
        try:
            with httpx.Client() as client:
                response = client.post(
                    "https://cms2.kbw.hbjt.com.cn/hyq/post/dealEdit",
                    headers={
                        "cookie": cookie,
                    },
                    data={
                        "mediaType": 0,
                        "createFlag": True,
                        "userId": fake_id,
                        "topicId": 289,
                        "imageId": 0,
                        "imgUrl": "?".join([ai_image_url, "768*768"]),
                        "coverFlag": True,
                        "postContent": " ".join(["#灵光火星生活#", prompt]),
                    },
                )
                response.raise_for_status()  # Raise an exception for HTTP errors
        except httpx.HTTPStatusError as exc:
            print(f"Error: {exc}")

        # Wait 7 to 23 seconds
        interval_random_number = random.randint(3, 11)
        print(f"Wait for {interval_random_number} seconds")
        time.sleep(interval_random_number)


if __name__ == "__main__":
    main()
