import os
import anthropic
def check_similarity6(headline, context):
    input_query = f"""i have two sentences sentence1 = {headline} sentence2 = {context} based on the exact specific subject matter and and dont consider specific meaning differences, is the first statement contextually similar in meaning to the second statement?, just say yes or no"""
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )
    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1000,
        temperature=0.0,
        system="Respond only in english.",
        messages=[
            {"role": "user", "content": input_query}
        ]
    )
    response_text = message.content[0].text
    print(input_query)
    response_text = response_text.lstrip()
    final_response = response_text
    print(response_text)
    if (final_response.lower().find('yes') != -1):
        return True
    return False