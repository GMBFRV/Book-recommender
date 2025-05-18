  // Get DOM elements (will be null if not on the respective page)
  const authorInput = document.getElementById("authorInput");
  const authorSuggestions = document.getElementById("authorSuggestions");
  const bookInput = document.getElementById("bookTitleInput");
  const bookSuggestions = document.getElementById("bookSuggestions");

  // Debounce function to limit API calls
  function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
  }

  // ================= AUTHOR SUGGESTIONS =================
  if (authorInput && authorSuggestions) {
    // Fetch author suggestions
    async function fetchAuthorSuggestions(query) {
      if (query.length < 2) {
        authorSuggestions.style.display = 'none';
        return;
      }

      try {
        const response = await fetch(`/api/author_suggest?query=${encodeURIComponent(query)}`);
        if (!response.ok) {
          console.error('Author suggestions API error:', response.status);
          return;
        }
        const authors = await response.json();
        console.log('Author suggestions response:', authors); // Debug log
        displayAuthorSuggestions(authors);
      } catch (err) {
        console.error('Error fetching author suggestions:', err);
      }
    }

    // Display author suggestions
    function displayAuthorSuggestions(authors) {
      if (!authors || authors.length === 0) {
        authorSuggestions.style.display = 'none';
        return;
      }

      authorSuggestions.innerHTML = authors.map(author => `
        <div class="suggestion-item" data-name="${author.name}">
          ${author.name}
        </div>
      `).join('');

      authorSuggestions.style.display = 'block';

      // Add click handlers to suggestions
      document.querySelectorAll('#authorSuggestions .suggestion-item').forEach(item => {
        item.addEventListener('click', () => {
          authorInput.value = item.dataset.name;
          authorSuggestions.style.display = 'none';
          const searchBtn = document.getElementById("searchAuthorBtn");
          if (searchBtn) searchBtn.click();
        });
      });
    }

    // Set up event listeners for author input
    authorInput.addEventListener('input', debounce(() => {
      fetchAuthorSuggestions(authorInput.value.trim());
    }, 300));

    // Show suggestions when focusing input
    authorInput.addEventListener('focus', () => {
      if (authorInput.value.trim().length >= 2) {
        fetchAuthorSuggestions(authorInput.value.trim());
      }
    });
  }

  // ================= BOOK SUGGESTIONS =================
  if (bookInput && bookSuggestions) {
    // Fetch book suggestions
    async function fetchBookSuggestions(query) {
      if (query.length < 2) {
        bookSuggestions.style.display = 'none';
        return;
      }

      try {
        const response = await fetch(`/api/book_suggest?query=${encodeURIComponent(query)}`);
        if (!response.ok) {
          console.error('Book suggestions API error:', response.status);
          return;
        }
        const books = await response.json();
        console.log('Book suggestions response:', books); // Debug log
        displayBookSuggestions(books);
      } catch (err) {
        console.error('Error fetching book suggestions:', err);
      }
    }

    // Display book suggestions
    function displayBookSuggestions(books) {
      if (!books || books.length === 0) {
        bookSuggestions.style.display = 'none';
        return;
      }

      bookSuggestions.innerHTML = books.map(book => `
        <div class="suggestion-item" data-title="${book.title}">
          ${book.cover_id ? 
            `<img src="https://covers.openlibrary.org/b/id/${book.cover_id}-S.jpg" 
                  alt="${book.title}" class="suggestion-cover">` : 
            `<div class="suggestion-cover placeholder"></div>`}
          <div class="suggestion-text">
            <div class="suggestion-title">${book.title}</div>
            ${book.author_name ? `<div class="suggestion-author">${book.author_name[0]}</div>` : ''}
          </div>
        </div>
      `).join('');

      bookSuggestions.style.display = 'block';

      // Add click handlers to suggestions
      document.querySelectorAll('#bookSuggestions .suggestion-item').forEach(item => {
        item.addEventListener('click', () => {
          bookInput.value = item.dataset.title;
          bookSuggestions.style.display = 'none';
          const searchBtn = document.getElementById("searchBtn");
          if (searchBtn) searchBtn.click();
        });
      });
    }

    // Set up event listeners for book input
    bookInput.addEventListener('input', debounce(() => {
      fetchBookSuggestions(bookInput.value.trim());
    }, 300));

    // Show suggestions when focusing input
    bookInput.addEventListener('focus', () => {
      if (bookInput.value.trim().length >= 2) {
        fetchBookSuggestions(bookInput.value.trim());
      }
    });
  }

  // ================= COMMON CLICK-OUTSIDE HANDLER =================
  document.addEventListener('click', (e) => {
    // Hide author suggestions if clicking outside
    if (authorSuggestions && !authorInput.contains(e.target) && !authorSuggestions.contains(e.target)) {
      authorSuggestions.style.display = 'none';
    }

    // Hide book suggestions if clicking outside
    if (bookSuggestions && !bookInput.contains(e.target) && !bookSuggestions.contains(e.target)) {
      bookSuggestions.style.display = 'none';
    }
  });