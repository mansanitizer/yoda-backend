document.addEventListener('DOMContentLoaded', () => {
    const crowd1 = document.querySelector('.crowd');
    const crowd2 = document.querySelector('.crowd2');
    const userIdInput = document.querySelector('#userIdInput');
    const lookupUserButton = document.querySelector('#lookupUserButton');
    const userLookupResult = document.querySelector('#userLookupResult');

    function getRandomEmoji() {
        const start = 0x1F600;
        const end = 0x1F64F;
        const codePoint = Math.floor(Math.random() * (end - start + 1)) + start;
        return String.fromCodePoint(codePoint);
    }

    const numEmojis = 500; 

    let crowd1Content = '';
    let crowd2Content = '';

    for (let i = 0; i < numEmojis; i++) {
        crowd1Content += getRandomEmoji();
        crowd2Content += getRandomEmoji();
    }

    crowd1.textContent = crowd1Content;
    crowd2.textContent = crowd2Content;

    if (lookupUserButton && userIdInput && userLookupResult) {
        lookupUserButton.addEventListener('click', async () => {
            const userId = userIdInput.value.trim();
            if (!userId) {
                userLookupResult.textContent = 'Enter a user ID first.';
                return;
            }

            userLookupResult.textContent = 'Loading username...';

            try {
                const response = await fetch(`/users/${encodeURIComponent(userId)}`);
                const payload = await response.json();

                if (!response.ok) {
                    userLookupResult.textContent = payload.message || 'Unable to fetch username.';
                    return;
                }

                userLookupResult.textContent = `Username: ${payload.username}`;
            } catch (error) {
                userLookupResult.textContent = 'Request failed while fetching username.';
            }
        });
    }
});
