/*
---------------------------------------- Genre-based Filter (Updated) ----------------------------------------
*/

document.addEventListener("DOMContentLoaded", () => {
  const genreButtons = document.querySelectorAll(".genre-btn");
  const continueBtn = document.getElementById("continueBtn");
  const out = document.getElementById("results");
    let selectedGenres = new Set();
    let offset = 0;
    const limit = 20;

  // Function to create a standardized book card element
  function createBookCard(book) {
    const card = document.createElement("div");
    card.className = "book-card";

    // Create the link wrapper
    const link = document.createElement("a");
    link.href = `/book/${book.key.replace("/works/","")}`;
    link.className = "book-link";

    // Book cover
    if (book.cover_id) {
      const img = document.createElement("img");
      img.src = `https://covers.openlibrary.org/b/id/${book.cover_id}-M.jpg`;
      img.alt = `Cover for ${book.title}`;
      img.className = "book-cover";
      img.loading = "lazy";
      const wrapper = document.createElement("div");
      wrapper.className = "cover-wrapper";
      wrapper.appendChild(img);
      link.appendChild(wrapper);

    } else {
      const placeholder = document.createElement("div");
      placeholder.className = "book-cover placeholder";
      link.appendChild(placeholder);
    }

    // Book information container
    const info = document.createElement("div");
    info.className = "book-info";

    // Title
    const h3 = document.createElement("h3");
    h3.textContent = book.title || "No title available";
    info.appendChild(h3);

    // Authors
    const pAuthor = document.createElement("p");
    pAuthor.textContent = (book.authors || []).join(", ") || "Unknown author";
    pAuthor.className = "book-authors";
    info.appendChild(pAuthor);

    // Rating (if available)
    if (book.rating) {
      const pRating = document.createElement("p");
      pRating.textContent = `★ ${book.rating.toFixed(1)}`;
      pRating.className = "book-rating";
      info.appendChild(pRating);
    }

    link.appendChild(info);
    card.appendChild(link);

    return card;
  }

  // Handle genre button selection
  genreButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const genre = btn.dataset.genre;
      if (selectedGenres.has(genre)) {
        selectedGenres.delete(genre);
        btn.classList.remove("selected");
      } else {
        selectedGenres.add(genre);
        btn.classList.add("selected");
      }
      continueBtn.disabled = selectedGenres.size === 0;
    });
  });

  // Handle "Find Books" button click
   continueBtn.addEventListener("click", () => {
    offset = 0;                  // при новом поиске начинаем сначала
    out.innerHTML = "";          // чистим результаты
    loadMoreBtn.hidden = true;   // прячем Load More, пока нет ответа
    fetchBooks();
  });

  // Вешаем на “Load More”
  loadMoreBtn.addEventListener("click", () => {
    fetchBooks();
  });

  // Универсальная функция запроса
  async function fetchBooks() {
    const genresArray = Array.from(selectedGenres);
    const params = new URLSearchParams();
    genresArray.forEach(g => params.append("genres", g));
    params.append("offset", offset);
    params.append("limit", limit);

    // Показываем индикатор (для первого запроса)
    if (offset === 0) {
      out.innerHTML = `
        <div class="loading-container">
          <div class="loading">
            <div class="loading-spinner"></div>
            <div class="loading-message">Searching for books...</div>
          </div>
        </div>`;
    }

    try {
      const resp = await fetch(`/api/genre_filter?${params.toString()}`);
      if (!resp.ok) throw new Error(`Error ${resp.status}`);
      const books = await resp.json();

      // Если первый запрос и нет результатов
      if (offset === 0 && books.length === 0) {
        out.innerHTML = '<div class="empty-message">No books found matching your selected genres.</div>';
        return;
      }

      // Убираем индикатор (после первого запроса)
      if (offset === 0) out.innerHTML = "";

      // Добавляем карточки
      books.forEach(book => {
        out.appendChild(createBookCard(book));
      });

      offset += books.length;   // сдвигаем offset на число реально полученных

      // Если получили меньше pageSize — дальше нечего грузить
      if (books.length < limit) {
        loadMoreBtn.hidden = true;
      } else {
        loadMoreBtn.hidden = false;
      }
    } catch (err) {
      if (offset === 0) {
        out.innerHTML = `<div class="error-message">Error: ${err.message}</div>`;
      } else {
        // при загрузке следующей порции можно просто отключить кнопку
        loadMoreBtn.hidden = true;
        console.error(err);
      }
    }
  }
});


/*
---------------------------------------- Author-based -----------------------------------------------------------------
 */

document.addEventListener("DOMContentLoaded", () => {
    const searchAuthorBtn = document.getElementById("searchAuthorBtn");
    const authorInput = document.getElementById("authorInput");
    const authorResults = document.getElementById("authorResults");

    if (searchAuthorBtn && authorInput && authorResults) {
        searchAuthorBtn.addEventListener("click", async () => {
            const authorName = authorInput.value.trim();

            // Input validation
            if (authorName.length < 2) {
                authorResults.innerHTML = '<div class="error-message">Please enter at least 2 characters</div>';
                return;
            }

                authorResults.innerHTML = `
                    <div class="loading">
                        <div class="loading-spinner"></div>
                        <div class="loading-message">Searching for authors...</div>
                   </div>
                `;


            try {
                const response = await fetch(`/api/author?author=${encodeURIComponent(authorName)}`);

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || "Server error");
                }

                const authors = await response.json();

                if (!authors.length) {
                    authorResults.innerHTML = `
                        <div class="empty-message">
                            No similar authors found for "${authorName}"
                        </div>
                    `;
                    return;
                }

                // In the author search results section
                authorResults.innerHTML = `
                <h3>Authors similar to ${authorName}:</h3>
                <div class="authors-grid">
                ${authors.map(author => `
                    <div class="author-card">
                        <a href="/author/${author.key}">
                            ${author.photo_id
                                ? `<img src="https://covers.openlibrary.org/a/olid/${author.key}-M.jpg"
                                    alt="${author.name}" class="author-photo">`
                                : `<img src="/static/images/no-photo-author.jpg"
                                    alt="Default author image" class="author-photo placeholder">`
                            }
                        <h4>${author.name}</h4>
                        ${author.top_work ? `<p class="author-work">Known for: ${author.top_work}</p>` : ''}
                        ${author.rating ? `<p class="author-rating">Avg rating: ${author.rating.toFixed(1)}</p>` : ''}
                        </a>
                    </div>
                `).join('')}
               </div>
                `;
            } catch (err) {
                authorResults.innerHTML = `
                    <div class="error-message">
                        Error: ${err.message || "Unknown error occurred"}
                    </div>
                `;
            }
        });
    }
});

/*
---------------------------------------- Book-based -----------------------------------------------------------------
 */
document.addEventListener("DOMContentLoaded", () => {
  const bookInput = document.getElementById("bookTitleInput");
  const searchBtn = document.getElementById("searchBtn");
  const resultsContainer = document.getElementById("results");

  async function performSearch() {
    const title = bookInput.value.trim();
    if (!title) {
      resultsContainer.innerHTML = '<div class="error-message">Please enter a book title</div>';
      return;
    }

    resultsContainer.innerHTML = `
        <div class="loading-container">
            <div class="loading">
            <div class="loading-spinner"></div>
            <div class="loading-message">Searching for books...</div>
            </div>
        </div>
    `;


    try {
      const response = await fetch(`/api/book?book=${encodeURIComponent(title)}`);
      if (!response.ok) throw new Error(`Error ${response.status}`);
      const books = await response.json();
      if (!books.length) {
        resultsContainer.innerHTML = `<div class="empty-message">No similar books found for "${title}"</div>`;
        return;
      }
      resultsContainer.innerHTML = "";

books.forEach(book => {
    const card = document.createElement("div");
    card.className = "book-card";

    // Create link wrapper
    const link = document.createElement("a");
    link.href = `/book/${book.key.replace("/works/","")}`;
    link.className = "book-link";

    // Book cover
    if (book.cover_id) {
      const img = document.createElement("img");
      img.src = `https://covers.openlibrary.org/b/id/${book.cover_id}-M.jpg`;
      img.alt = `Cover for ${book.title}`;
      img.className = "book-cover";
      img.loading = "lazy";
      const wrapper = document.createElement("div");
      wrapper.className = "cover-wrapper";
      wrapper.appendChild(img);
      link.appendChild(wrapper);
    } else {
        const placeholder = document.createElement("div");
        placeholder.className = "book-cover placeholder";
        link.appendChild(placeholder);
    }

    // Book info
    const info = document.createElement("div");
    info.className = "book-info";

    // Title
    const h3 = document.createElement("h3");
    h3.textContent = book.title || "No title available";
    info.appendChild(h3);

    // Authors
    const pAuthor = document.createElement("p");
    pAuthor.textContent = book.authors?.join(", ") || "Unknown author";
    pAuthor.className = "book-authors";
    info.appendChild(pAuthor);

    // Rating
    if (book.rating) {
        const pRating = document.createElement("p");
        pRating.textContent = `★ ${book.rating.toFixed(1)}`;
        pRating.className = "book-rating";
        info.appendChild(pRating);
    }

    link.appendChild(info);
    card.appendChild(link);
    resultsContainer.appendChild(card);
});
    } catch (err) {
      resultsContainer.innerHTML = `<div class="error-message">Error: ${err.message}</div>`;
    }
  }

  searchBtn.addEventListener("click", performSearch);
  bookInput.addEventListener("keydown", e => {
    if (e.key === "Enter") performSearch();
  });
});