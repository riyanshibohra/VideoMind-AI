from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from src.utils import get_video_context

def create_chat_prompt():
    """Create the chat prompt template"""
    prompt_template = """You are a helpful AI assistant that answers questions about YouTube videos based on their transcripts. 
    Use the following pieces of context from the video transcript to answer the question. If you don't know the answer, just say that 
    you don't know, don't try to make up an answer.

    Context from video: {context}

    Previous conversation:
    {chat_history}

    Human: {question}
    Assistant:"""
    
    return PromptTemplate(
        input_variables=["context", "chat_history", "question"],
        template=prompt_template
    )

def get_chatbot(video_url):
    """Create a chatbot instance for the video"""
    # Create LLM
    llm = ChatOpenAI(
        model_name="gpt-3.5-turbo",
        temperature=0.7
    )
    
    # Create memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        input_key="question"
    )
    
    # Create prompt
    prompt = create_chat_prompt()
    
    # Create conversation chain
    conversation = LLMChain(
        llm=llm,
        prompt=prompt,
        memory=memory,
        verbose=False
    )
    
    def get_response(user_input):
        # Get relevant context from vector store
        context = get_video_context(user_input, video_url)
        
        # Get response
        response = conversation.predict(
            context=context,
            question=user_input
        )
        
        return response
    
    return get_response 