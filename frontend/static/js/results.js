/* ---------------------------------------------------------------------------------------------------------------------
---------------------------------------- Genre-based -------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------*/

document.addEventListener("DOMContentLoaded", () => {
  /**
 * Enable genre-based book discovery with dynamic filtering and pagination.

 * This script attaches interactive behavior to the genre selection interface
 * and fetches books from the server based on selected genres.

 * Functionality includes:
 * 1. Tracks selected genres using button toggles.
 * 2. Enables or disables the "Find Books" button depending on whether any genres are selected.
 * 3. On "Find Books" click:
 *    - Resets current state.
 *    - Sends an API request with selected genres and fetches the first page of books.
 *    - Displays results in a card-based layout with title, authors, cover, and rating.
 * 4. On "Load More" click:
 *    - Fetches the next set of results using an updated offset.
 *    - Appends the new results without clearing previous ones.
 * 5. Dynamically hides or shows the "Load More" button depending on whether more results are available.
 * 6. Handles empty results and errors with user-friendly messages.
 */

  const genreButtons = document.querySelectorAll(".genre-btn");
  const continueBtn = document.getElementById("continueBtn");
  const loadMoreBtn = document.getElementById("loadMoreBtn");
  const out = document.getElementById("results");

  let selectedGenres = new Set();
  let offset = 0;
  const limit = 20;

  // Create a standardized book card DOM element
  function createBookCard(book) {
    const card = document.createElement("div");
    card.className = "book-card";

    const link = document.createElement("a");
    link.href = `/book/${book.key.replace("/works/", "")}`;
    link.className = "book-link";

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

    const info = document.createElement("div");
    info.className = "book-info";

    const h3 = document.createElement("h3");
    h3.textContent = book.title || "No title available";
    info.appendChild(h3);

    const pAuthor = document.createElement("p");
    pAuthor.textContent = (book.authors || []).join(", ") || "Unknown author";
    pAuthor.className = "book-authors";
    info.appendChild(pAuthor);

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

  // Handle genre button selection/deselection
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

  // Handle "Find Books" click — reset state and load first page
  continueBtn.addEventListener("click", () => {
    offset = 0;
    out.innerHTML = "";
    loadMoreBtn.style.display = "none";
    fetchBooks();
  });

  // Handle "Load More" click — fetch next page
  loadMoreBtn.addEventListener("click", () => {
    loadMoreBtn.disabled = true;
    fetchBooks().then(() => {
      loadMoreBtn.disabled = false;
    });
  });

  // Fetch books from the API using current genre selections and offset
  async function fetchBooks() {
    const genresArray = Array.from(selectedGenres);
    const params = new URLSearchParams();
    genresArray.forEach(g => params.append("genres", g));
    params.append("offset", offset);
    params.append("limit", limit);

    // Show loading animation for initial search
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

      if (offset === 0 && books.length === 0) {
        out.innerHTML = '<div class="empty-message">No books found matching your selected genres.</div>';
        return;
      }

      if (offset === 0) {
        out.innerHTML = "";
      }

      books.forEach(book => {
        out.appendChild(createBookCard(book));
      });

      offset += books.length;

      // Show or hide Load More button depending on result size
      loadMoreBtn.style.display = books.length < limit ? "none" : "block";

    } catch (err) {
      if (offset === 0) {
        out.innerHTML = `<div class="error-message">Error: ${err.message}</div>`;
      } else {
        loadMoreBtn.style.display = "none";
        console.error(err);
      }
    }
  }

  // Hide Load More button on initial page load
  loadMoreBtn.style.display = "none";
});




/* ---------------------------------------------------------------------------------------------------------------------
---------------------------------------- Author-based -------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------*/

document.addEventListener("DOMContentLoaded", () => {
  /**
 * Enable interactive author search and display of similar authors based on user input.

 * This script is triggered when the DOM is fully loaded and provides the following functionality:
 * 1. Validates the author's name entered by the user in the input field.
 * 2. On "Search" button click:
 *    - Sends a request to `/api/author?author={authorName}` to fetch similar authors.
 *    - Displays a loading animation while waiting for the response.
 *    - If results are found:
 *        • Renders a grid of author cards with photo, name, known work, and average rating.
 *    - If no results are found:
 *        • Displays a friendly message indicating no similar authors were found.
 * 3. Handles invalid input (less than 2 characters) and server-side or network errors with clear feedback.
 */
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


/* ---------------------------------------------------------------------------------------------------------------------
---------------------------------------- Book-based -------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------*/

document.addEventListener("DOMContentLoaded", () => {
  /**
 * Enable dynamic book search and paginated loading of similar book recommendations.

 * This script allows users to:
 * - Search for books based on a title input.
 * - Fetch the initial result set and render it as a grid of book cards.
 * - Load additional pages using the "Load More" button.
 * - Handle errors, loading states, and display fallback messages for empty results.
 */
  const bookInput        = document.getElementById("bookTitleInput");
  const searchBtn        = document.getElementById("searchBtn");
  const loadMoreBtn      = document.getElementById("loadMoreBtn");
  const resultsContainer = document.getElementById("results");

  if (!bookInput || !searchBtn) return;

  let offset       = 0;
  const pageSize   = 20;
  let currentQuery = "";

  loadMoreBtn.style.display  = "none";
  loadMoreBtn.disabled       = true;

  async function fetchBooks(reset = false) {
    const title = bookInput.value.trim();
    if (!title) return;

    if (reset) {
      offset = 0;
      currentQuery = title;
      resultsContainer.innerHTML = "";
      loadMoreBtn.style.display = "none";
      loadMoreBtn.disabled      = true;
    } else {
      loadMoreBtn.disabled      = true;
      loadMoreBtn.classList.add("loading");
    }

    if (reset) {
      resultsContainer.innerHTML = `
        <div class="loading-container">
          <div class="loading">
            <div class="loading-spinner"></div>
            <div class="loading-message">Searching for books…</div>
          </div>
        </div>`;
    }

    try {
      const url = `/api/book?book=${encodeURIComponent(currentQuery)}&offset=${offset}&limit=${pageSize}`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }
      const books = await response.json();

      if (reset && books.length === 0) {
        resultsContainer.innerHTML = `
          <div class="empty-message">
            No similar books found for “${currentQuery}”
          </div>`;
        return;
      }

      if (reset) {
        resultsContainer.innerHTML = "";
      }

      books.forEach(book => {
        const card = document.createElement("div");
        card.className = "book-card";

        const link = document.createElement("a");
        link.href      = `/book/${book.key.replace("/works/","")}`;
        link.className = "book-link";

        if (book.cover_id) {
          const wrapper = document.createElement("div");
          wrapper.className = "cover-wrapper";

          const img = document.createElement("img");
          img.src       = `https://covers.openlibrary.org/b/id/${book.cover_id}-M.jpg`;
          img.alt       = `Cover for ${book.title}`;
          img.className = "book-cover";
          img.loading   = "lazy";

          wrapper.appendChild(img);
          link.appendChild(wrapper);
        } else {
          const placeholder = document.createElement("div");
          placeholder.className = "book-cover placeholder";
          link.appendChild(placeholder);
        }

        const info = document.createElement("div");
        info.className = "book-info";

        const h3 = document.createElement("h3");
        h3.textContent = book.title || "No title available";
        info.appendChild(h3);

        const pAuthor = document.createElement("p");
        pAuthor.className = "book-authors";
        pAuthor.textContent = (book.authors?.join(", ") || "Unknown author");
        info.appendChild(pAuthor);

        if (book.rating != null) {
          const pRating = document.createElement("p");
          pRating.className = "book-rating";
          pRating.textContent = `★ ${book.rating.toFixed(1)}`;
          info.appendChild(pRating);
        }

        link.appendChild(info);
        card.appendChild(link);
        resultsContainer.appendChild(card);
      });

      if (books.length === pageSize) {
        loadMoreBtn.style.display = "block";
      } else {
        loadMoreBtn.style.display = "none";
        const endMsg = document.createElement("div");
        endMsg.className = "end-message";
        endMsg.textContent = "No more books found.";
        resultsContainer.appendChild(endMsg);
      }

      offset += books.length;

    } catch (err) {
      resultsContainer.innerHTML = "";
      const errDiv = document.createElement("div");
      errDiv.className = "error-message";
      errDiv.textContent = `Error: ${err.message}`;
      resultsContainer.appendChild(errDiv);
      loadMoreBtn.style.display = "none";

    } finally {
      loadMoreBtn.disabled = false;
      loadMoreBtn.classList.remove("loading");
    }
  }

  searchBtn.addEventListener("click", () => fetchBooks(true));
  bookInput.addEventListener("keydown", e => {
    if (e.key === "Enter") fetchBooks(true);
  });
  loadMoreBtn.addEventListener("click", () => fetchBooks(false));
});
