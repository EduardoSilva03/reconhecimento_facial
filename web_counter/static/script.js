setInterval(() => {
    fetch('/count')
        .then(response => response.json())
        .then(data => {
            document.getElementById('count').textContent = data.count;
        });
}, 1000);