from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from src.utils import get_video_context

def create_chat_prompt():
    """Create the chat prompt template"""
    prompt_template = """You are a helpful AI assistant that answers questions about YouTube videos based on their transcripts. 
    Use the following pieces of context from the video transcripts to answer the question. Each piece of context includes the source video URL.
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    When answering, try to combine information from multiple videos if relevant.
    
    The videos in the current session are:
    {video_list}
    
    Context from videos:
    {context}

    Previous conversation:
    {chat_history}

    Human: {question}
    Assistant:"""
    
    return PromptTemplate(
        input_variables=["video_list", "context", "chat_history", "question"],
        template=prompt_template
    )

def get_chatbot(session_id):
    """Create a chatbot instance for the session"""
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
        context = get_video_context(user_input, session_id)
        
        # Get list of current videos
        from app import st
        video_list = "\n".join([
            f"- {st.session_state.video_titles.get(url, 'Untitled Video')} ({url})"
            for url in st.session_state.processed_urls
        ])
        
        # Get response
        response = conversation.predict(
            video_list=video_list,
            context=context,
            question=user_input
        )
        
        return response
    
    return get_response 