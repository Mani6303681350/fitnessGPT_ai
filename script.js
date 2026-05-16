const chat =
document.getElementById("chatContainer");

/* Load Chats */

async function loadChats(){

    let response =
    await fetch("/get_chats");

    let data =
    await response.json();

    // Sidebar

    let list =
    document.getElementById("chatList");

    list.innerHTML = "";

    data.chats.forEach(chatName => {

        // Get Messages

        let messages =
        data.current === chatName
        ? data.messages
        : [];

        // First User Message

        let displayName =
        messages.length > 0
        ? messages[0].content
        : chatName;

        list.innerHTML += `
        <div class="chat-item"
            onclick="switchChat('${chatName}')">

            ${displayName}

        </div>
        `;
    });

    // Show Current Messages

    showMessages(data.messages);
}

/* Show Messages */

function showMessages(messages){

    chat.innerHTML = "";

    messages.forEach(msg => {

        chat.innerHTML += `
        <div class="${
            msg.role === "user"
            ? "user-message"
            : "bot-message"
        }">

            ${msg.content}

        </div>
        `;
    });

    // Auto Scroll

    chat.scrollTop =
    chat.scrollHeight;
}

/* Send Message */

async function sendMessage(){

    let input =
    document.getElementById("userInput");

    let message =
    input.value.trim();

    if(message === "") return;

    input.value = "";

    await fetch("/chat",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify({
            message:message
        })
    });

    loadChats();
}

/* New Chat */

async function newChat(){

    await fetch("/new_chat",{
        method:"POST"
    });

    loadChats();
}

/* Switch Chat */

async function switchChat(chatName){

    let response =
    await fetch("/switch_chat",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify({
            chat:chatName
        })
    });

    let data =
    await response.json();

    showMessages(data.messages);
}

/* Voice Input */

function startVoice(){

    let recognition =
    new webkitSpeechRecognition();

    recognition.lang = "en-US";

    recognition.start();

    recognition.onresult = function(event){

        document.getElementById("userInput")
        .value =
        event.results[0][0].transcript;
    };
}

/* Enter Key */

document
.getElementById("userInput")
.addEventListener("keypress", function(e){

    if(e.key === "Enter"){
        sendMessage();
    }
});

/* Start */

loadChats();