console.log('Hello world!');

const ws = new WebSocket('ws://localhost:8080');

formChat.addEventListener('submit', (e) => {
    e.preventDefault();
    ws.send(textField.value);
    textField.value = "";
});

ws.onopen = () => {
    console.log('Connected to WebSocket server');
};

ws.onmessage = (event) => {
    console.log(event.data);

    const elMsg = document.createElement('pre'); // <pre> зберігає форматування
    elMsg.textContent = event.data;
    subscribe.appendChild(elMsg);
};
