import os
from dotenv import load_dotenv
from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from google import genai


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not found in .env")

client = genai.Client(api_key=api_key)


class InquiryState(TypedDict):
    customer_message :str
    category : str
    next_action : str
    customer_reply : str

def classify_inquiry(state: InquiryState):
    message = state["customer_message"]

    prompt = f"""
    You are a customer support classifier.

    Classify the customer message into exactly one category:
    refund, pricing, support, general.

    Customer message: {message}

    Return only the category name.
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    category = response.text.strip().lower()

    if category not in ["refund", "pricing", "support", "general"]:
        category = "general"

    return {
        "customer_message": message,
        "category": category,
        "next_action": state["next_action"]
}


def decide_action(state: InquiryState):
    if state["category"] == "refund":
        action = "human_review"
    elif state["category"] == "support":
        action = "support_team"
    else:
        action = "reply_to_customer"

    return {"next_action": action}


def generate_customer_reply(state: InquiryState):
    message = state["customer_message"]
    category = state["category"]

    
    response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=(
        f"Customer message: {message}\n"
        f"Inquiry category: {category}"
    ),
    config=genai.types.GenerateContentConfig(
        system_instruction=(
            "You are a professional and friendly customer support assistant. "
            "Write short, helpful replies. Never invent company policies, "
            "prices, order details, or actions that have not happened. "
            "Never claim a request was forwarded or approved unless confirmed."
        )
    )
)

    return {"customer_reply": response.text.strip()}



graph_builder = StateGraph(InquiryState)

graph_builder.add_node("classify", classify_inquiry)
graph_builder.add_node("decide", decide_action)
graph_builder.add_node("reply", generate_customer_reply)

graph_builder.add_edge(START,"classify")
graph_builder.add_edge("classify","decide")
graph_builder.add_edge("decide","reply")
graph_builder.add_edge("reply",END)


agent = graph_builder.compile()

if __name__ == "__main__":
    result = agent.invoke({
        "customer_message": "I want a refund for my order",
        "category": "",
        "next_action": "",
        "customer_reply":""
    })

    
    print("\n--- CUSTOMER INQUIRY RESULT ---")
    print("Message:", result["customer_message"])
    print("Category:", result["category"])
    print("Next action:", result["next_action"])
    print("AI reply:", result["customer_reply"])

