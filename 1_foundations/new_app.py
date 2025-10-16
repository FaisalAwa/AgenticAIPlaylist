from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
from flask import Flask, request, jsonify, render_template_string

load_dotenv(override=True)

def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )

def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            },
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]

class Me:
    def __init__(self):
        self.openai = OpenAI()
        self.name = "Faisal Mehmood Awan"
        reader = PdfReader("me/Profile.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()

    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results
    
    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt
    
    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            if response.choices[0].finish_reason=="tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        return response.choices[0].message.content

# Flask App Integration
app = Flask(__name__)
me = Me()

# HTML Template (embedded in Python file for simplicity)
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat with Faisal Mehmood Awan</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .chat-container {
            width: 100%;
            max-width: 900px;
            height: 90vh;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .chat-header {
            background: linear-gradient(135deg, #4f46e5, #7c3aed);
            padding: 28px 32px;
            color: white;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .chat-header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
            animation: shimmer 8s ease-in-out infinite;
        }

        .header-content {
            position: relative;
            z-index: 2;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
        }

        .header-avatar {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #ffffff, #f8fafc);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-5px); }
        }

        .header-text {
            text-align: left;
        }

        @keyframes shimmer {
            0%, 100% { transform: rotate(0deg); }
            50% { transform: rotate(180deg); }
        }

        .chat-header h1 {
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 8px;
            position: relative;
            z-index: 1;
        }

        .chat-header p {
            opacity: 0.9;
            font-size: 1rem;
            position: relative;
            z-index: 1;
        }

        .chat-messages {
            flex: 1;
            padding: 24px;
            overflow-y: auto;
            scroll-behavior: smooth;
        }

        .message {
            display: flex;
            margin-bottom: 24px;
            animation: fadeInUp 0.5s ease-out;
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .message.user {
            flex-direction: row-reverse;
        }

        .message-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 12px;
            flex-shrink: 0;
            position: relative;
            overflow: hidden;
            border: 3px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }

        .message-avatar:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 25px rgba(0, 0, 0, 0.15);
        }

        .message.user .message-avatar {
            background: linear-gradient(135deg, #10b981, #059669);
            border-color: rgba(16, 185, 129, 0.3);
        }

        .message.assistant .message-avatar {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            border-color: rgba(99, 102, 241, 0.3);
            animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% {
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1), 0 0 0 0 rgba(99, 102, 241, 0.4);
            }
            50% {
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1), 0 0 0 8px rgba(99, 102, 241, 0);
            }
        }

        .avatar-svg {
            width: 28px;
            height: 28px;
            fill: white;
        }

        .message-content {
            max-width: 70%;
            padding: 18px 24px;
            border-radius: 24px;
            line-height: 1.6;
            position: relative;
            word-wrap: break-word;
            white-space: pre-wrap;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }

        .message-content:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }

        .message.user .message-content {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            border-bottom-right-radius: 8px;
            position: relative;
            overflow: hidden;
        }

        .message.user .message-content::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, rgba(255,255,255,0.1) 0%, transparent 100%);
            pointer-events: none;
        }

        .message.assistant .message-content {
            background: linear-gradient(135deg, #f8fafc, #ffffff);
            color: #1e293b;
            border: 1px solid #e2e8f0;
            border-bottom-left-radius: 8px;
            position: relative;
        }

        .message.assistant .message-content::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            height: 3px;
            width: 100%;
            background: linear-gradient(90deg, #6366f1, #8b5cf6, #6366f1);
            background-size: 200% 100%;
            animation: shimmer-line 3s ease-in-out infinite;
        }

        @keyframes shimmer-line {
            0%, 100% { background-position: 200% 0; }
            50% { background-position: -200% 0; }
        }

        .typing-indicator {
            display: none;
            align-items: center;
            margin-left: 52px;
            margin-bottom: 20px;
        }

        .typing-indicator.active {
            display: flex;
        }

        .typing-dots {
            display: flex;
            align-items: center;
            padding: 16px 20px;
            background: #f8fafc;
            border-radius: 20px;
            border: 1px solid #e2e8f0;
        }

        .typing-dots span {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #94a3b8;
            margin: 0 2px;
            animation: typing 1.4s ease-in-out infinite;
        }

        .typing-dots span:nth-child(2) {
            animation-delay: 0.2s;
        }

        .typing-dots span:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes typing {
            0%, 60%, 100% {
                transform: translateY(0);
                opacity: 0.4;
            }
            30% {
                transform: translateY(-10px);
                opacity: 1;
            }
        }

        .chat-input-container {
            padding: 24px 32px;
            background: #ffffff;
            border-top: 1px solid #e2e8f0;
        }

        .chat-input-wrapper {
            display: flex;
            align-items: flex-end;
            gap: 12px;
            background: #f8fafc;
            border-radius: 24px;
            padding: 8px;
            border: 2px solid transparent;
            transition: all 0.3s ease;
        }

        .chat-input-wrapper:focus-within {
            border-color: #6366f1;
            background: white;
            box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
        }

        .chat-input {
            flex: 1;
            border: none;
            outline: none;
            padding: 12px 16px;
            font-size: 16px;
            background: transparent;
            resize: none;
            max-height: 120px;
            min-height: 20px;
            font-family: inherit;
            line-height: 1.5;
        }

        .send-button {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            flex-shrink: 0;
            position: relative;
            overflow: hidden;
        }

        .send-button::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            transition: all 0.3s ease;
        }

        .send-button:hover:not(:disabled) {
            transform: scale(1.05) rotate(15deg);
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
        }

        .send-button:hover::before {
            width: 100%;
            height: 100%;
        }

        .send-button:active {
            transform: scale(0.95);
        }

        .send-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        .send-button svg {
            width: 22px;
            height: 22px;
            position: relative;
            z-index: 1;
        }

        .welcome-message {
            text-align: center;
            padding: 50px 20px;
            color: #64748b;
            animation: fadeIn 1s ease-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .welcome-message h2 {
            font-size: 2rem;
            color: #1e293b;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
        }

        .welcome-emoji {
            font-size: 2.5rem;
            animation: wave 2s ease-in-out infinite;
        }

        @keyframes wave {
            0%, 100% { transform: rotate(0deg); }
            25% { transform: rotate(-10deg); }
            75% { transform: rotate(10deg); }
        }

        .welcome-message p {
            line-height: 1.6;
            max-width: 500px;
            margin: 0 auto;
            font-size: 1.1rem;
        }

        .welcome-features {
            display: flex;
            justify-content: center;
            gap: 24px;
            margin-top: 32px;
            flex-wrap: wrap;
        }

        .feature-item {
            background: linear-gradient(135deg, #f8fafc, #ffffff);
            padding: 16px 20px;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            text-align: center;
            min-width: 120px;
            transition: all 0.3s ease;
        }

        .feature-item:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }

        .feature-icon {
            font-size: 1.5rem;
            margin-bottom: 8px;
            display: block;
        }

        .feature-text {
            font-size: 0.9rem;
            color: #64748b;
            font-weight: 500;
        }

        .error-message {
            color: #ef4444;
            background: linear-gradient(135deg, #fef2f2, #ffffff) !important;
            border: 1px solid #fecaca !important;
            position: relative;
        }

        .error-message::before {
            content: '⚠️';
            position: absolute;
            top: -8px;
            right: -8px;
            background: #ef4444;
            color: white;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            animation: bounce 1s infinite;
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
        }

        @keyframes fadeOut {
            from { opacity: 1; transform: translateY(0); }
            to { opacity: 0; transform: translateY(-20px); }
        }

        /* Particle effect for send button */
        .send-button.sending::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 4px;
            height: 4px;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 50%;
            animation: particle 0.6s ease-out;
        }

        @keyframes particle {
            0% {
                transform: translate(-50%, -50%) scale(0);
                opacity: 1;
            }
            100% {
                transform: translate(-50%, -50%) scale(10);
                opacity: 0;
            }
        }

        /* Smooth scroll enhancement */
        .chat-messages {
            scroll-behavior: smooth;
            scrollbar-width: thin;
            scrollbar-color: #cbd5e1 transparent;
        }

        /* Message status indicators */
        .message-status {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.7);
            margin-top: 4px;
            text-align: right;
        }

        .message.assistant .message-status {
            color: #94a3b8;
        }

        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            
            .chat-container {
                height: 95vh;
                border-radius: 16px;
            }
            
            .chat-header {
                padding: 20px 24px;
            }
            
            .chat-header h1 {
                font-size: 1.5rem;
            }
            
            .chat-messages {
                padding: 16px;
            }
            
            .message-content {
                max-width: 85%;
            }
            
            .chat-input-container {
                padding: 16px 20px;
            }
        }

        .chat-messages::-webkit-scrollbar {
            width: 6px;
        }

        .chat-messages::-webkit-scrollbar-track {
            background: transparent;
        }

        .chat-messages::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 3px;
        }

        .chat-messages::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <div class="header-content">
                <div class="header-avatar">
                
                                    <img src="/static/myimage.jpeg" alt="Faisal" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">

                
                </div>
                <div class="header-text">
                    <h1>Chat with Faisal Mehmood Awan</h1>
                    <p>Ask me about my background, skills, and experience</p>
                </div>
            </div>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="welcome-message">
                <h2><span class="welcome-emoji">👋</span>Welcome!</h2>
                <p>Hi there! I'm Faisal's AI assistant. Feel free to ask me anything about Faisal's professional background, skills, experience, or career. I'm here to help you learn more about him!</p>
                
                <div class="welcome-features">
                    <div class="feature-item">
                        <span class="feature-icon">💼</span>
                        <span class="feature-text">Career Info</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">🛠️</span>
                        <span class="feature-text">Skills & Tech</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">📧</span>
                        <span class="feature-text">Get In Touch</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="typing-indicator" id="typingIndicator">
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
        
        <div class="chat-input-container">
            <div class="chat-input-wrapper">
                <textarea 
                    id="chatInput" 
                    class="chat-input" 
                    placeholder="Type your message here..."
                    rows="1"
                ></textarea>
                <button id="sendButton" class="send-button">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                    </svg>
                </button>
            </div>
        </div>
    </div>

    <script>
        class ChatInterface {
            constructor() {
                this.chatMessages = document.getElementById('chatMessages');
                this.chatInput = document.getElementById('chatInput');
                this.sendButton = document.getElementById('sendButton');
                this.typingIndicator = document.getElementById('typingIndicator');
                this.conversationHistory = [];
                
                this.initializeEventListeners();
                this.autoResizeTextarea();
            }

            initializeEventListeners() {
                this.sendButton.addEventListener('click', () => this.sendMessage());
                this.chatInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        this.sendMessage();
                    }
                });
                
                this.chatInput.addEventListener('input', () => this.autoResizeTextarea());
            }

            autoResizeTextarea() {
                this.chatInput.style.height = '20px';
                this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
            }

            async sendMessage() {
                const message = this.chatInput.value.trim();
                if (!message) return;

                this.chatInput.value = '';
                this.autoResizeTextarea();
                this.sendButton.disabled = true;
                this.sendButton.classList.add('sending');
                
                this.addMessage(message, 'user');
                this.showTypingIndicator();

                try {
                    const response = await this.callChatAPI(message);
                    this.hideTypingIndicator();
                    this.addMessage(response, 'assistant');
                    
                    // Add a subtle sound effect (optional)
                    this.playNotificationSound();
                    
                } catch (error) {
                    this.hideTypingIndicator();
                    this.addMessage('Sorry, I encountered an error. Please try again.', 'assistant', true);
                    console.error('Chat error:', error);
                } finally {
                    this.sendButton.disabled = false;
                    this.sendButton.classList.remove('sending');
                    this.chatInput.focus();
                }
            }

            playNotificationSound() {
                // Create a subtle notification sound
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
                oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
                
                gainNode.gain.setValueAtTime(0, audioContext.currentTime);
                gainNode.gain.linearRampToValueAtTime(0.01, audioContext.currentTime + 0.01);
                gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.2);
                
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.2);
            }

            addMessage(content, sender, isError = false) {
                const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
                if (welcomeMessage && this.conversationHistory.length === 0) {
                    welcomeMessage.style.animation = 'fadeOut 0.5s ease-out';
                    setTimeout(() => welcomeMessage.remove(), 500);
                }

                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${sender}`;
                
                const avatar = document.createElement('div');
                avatar.className = 'message-avatar';
                
                if (sender === 'user') {
                    avatar.innerHTML = `
                


             <img src="/static/myimage.jpeg" alt="Faisal" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">

                    `;
                
                } else {
                    avatar.innerHTML = `
                        <svg class="avatar-svg" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12,1L3,5V11C3,16.55 6.84,21.74 12,23C17.16,21.74 21,16.55 21,11V5L12,1M12,7C13.4,7 14.8,8.6 14.8,10.1V11H16.2V16H7.8V11H9.2V10.1C9.2,8.6 10.6,7 12,7M12,8.2C11.2,8.2 10.4,8.7 10.4,10.1V11H13.6V10.1C13.6,8.7 12.8,8.2 12,8.2Z"/>
                        </svg>
                    `;
                }
                
                const messageContent = document.createElement('div');
                messageContent.className = 'message-content';
                
                if (isError) {
                    messageContent.className += ' error-message';
                }
                
                messageContent.textContent = content;
                
                messageDiv.appendChild(avatar);
                messageDiv.appendChild(messageContent);
                
                this.chatMessages.appendChild(messageDiv);
                this.scrollToBottom();
                
                this.conversationHistory.push({ role: sender === 'user' ? 'user' : 'assistant', content });
            }

            showTypingIndicator() {
                this.typingIndicator.classList.add('active');
                this.scrollToBottom();
            }

            hideTypingIndicator() {
                this.typingIndicator.classList.remove('active');
            }

            scrollToBottom() {
                setTimeout(() => {
                    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
                }, 100);
            }

            async callChatAPI(message) {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        history: this.conversationHistory
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                return data.response;
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            new ChatInterface();
        });
    </script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data['message']
        history = data.get('history', [])
        
        # Convert history to the format your Me class expects
        formatted_history = []
        for msg in history:
            if msg['role'] in ['user', 'assistant']:
                formatted_history.append({
                    "role": msg["role"], 
                    "content": msg["content"]
                })
        
        # Get response from your existing Me class
        response = me.chat(message, formatted_history)
        
        return jsonify({"response": response})
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    print("Starting Flask server...")
    print("Visit http://localhost:5000 to use the chat interface")
    app.run(debug=True, host='0.0.0.0', port=5000)