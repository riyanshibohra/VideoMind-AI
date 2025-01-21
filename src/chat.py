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
    
    The videos in the current session are:
    {video_list}
    
    Important Instructions:
    - Since you can see the list of videos above, you should know how many videos are loaded
    - If there is only one video, do NOT ask which video the user is referring to - it's obviously the only one loaded
    - Only ask for clarification about which video if there are multiple videos and the question could apply to more than one of them
    - When answering, try to combine information from multiple videos if relevant and if multiple videos are loaded
    
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

def format_video_list(videos_dict):
    """Format the video list for the prompt"""
    return "\n".join([
        f"- {info['title']} ({url})"
        for url, info in videos_dict.items()
    ])

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
    
    def get_response(user_input, videos_info=None):
        # Get relevant context from vector store
        context = get_video_context(user_input, session_id)
        
        # Format video list if provided
        video_list = format_video_list(videos_info) if videos_info else "No videos loaded"
        
        # Get response
        response = conversation.predict(
            video_list=video_list,
            context=context,
            question=user_input
        )
        
        return response
    
    return get_response 