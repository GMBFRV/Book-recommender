document.addEventListener("DOMContentLoaded", () => {
  const genreButtons = document.querySelectorAll(".genre-btn");
  const continueBtn = document.getElementById("continueBtn");
  const out = document.getElementById("results");
  let selectedGenres = new Set();

  // Genre selection toggle
  genreButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const g = btn.dataset.genre;
      if (selectedGenres.has(g)) {
        selectedGenres.delete(g);
        btn.classList.remove("selected");
      } else {
        selectedGenres.add(g);
        btn.classList.add("selected");
      }
      continueBtn.disabled = selectedGenres.size === 0;
    });
  });

  // Handle "Find Books" button click
  continueBtn.addEventListener("click", async () => {
    const genresArray = Array.from(selectedGenres);
    const params = new URLSearchParams();
    genresArray.forEach(g => params.append("genres", g));

    out.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <div class="loading-message">Searching for books...</div>
        </div>
    `;

    try {
      const resp = await fetch(`/api/genre_filter?${params.toString()}`);
      if (!resp.ok) throw new Error(`Error ${resp.status}`);
      const books = await resp.json();

      if (!books.length) {
        out.innerHTML = '<div class="empty-message">No books found matching your selected genres.</div>';
        return;
      }

      out.innerHTML = "";
      books.forEach(book => {
        const card = document.createElement("div");
        card.className = "book-card";

        // Title
        const h3 = document.createElement("h3");
        h3.textContent = book.title || "No title available";
        card.appendChild(h3);

        // Authors
        const pa = document.createElement("p");
        pa.textContent = (book.authors || []).join(", ") || "Author unknown";
        card.appendChild(pa);

        // Rating
        const pr = document.createElement("p");
        pr.textContent = `Rating: ${book.rating ?? "N/A"} (${book.rating_count ?? "N/A"} reviews)`;
        card.appendChild(pr);

        if (book.cover_id) {
          const img = document.createElement("img");
          img.src = `https://covers.openlibrary.org/b/id/${book.cover_id}-M.jpg`;
          img.alt = `Cover for ${book.title}`;
          img.loading = "lazy";
          card.appendChild(img);
        }

        // wrap the card in a link to /book/{key}
       const link = document.createElement("a");
       link.href      = `/book/${book.key.replace("/works/","")}`;
       link.className = "book-link";
       link.appendChild(card);

       out.appendChild(link);
      });
    } catch (err) {
      out.innerHTML = `<div class="error-message">Error: ${err.message}</div>`;
    }
  });
});

// Author search functionality
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

            authorResults.innerHTML = '<div class="loading-message">Searching for authors...</div>';

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
                            ${author.photo_id ? 
                                `<img src="https://covers.openlibrary.org/a/olid/${author.key}-M.jpg" 
                                    alt="${author.name}" class="author-photo">` : 
                            '<div class="author-photo placeholder"></div>'}
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
    resultsContainer.innerHTML = '<div class="loading-message">Searching for similar books...</div>';
    try {
      const response = await fetch(`/api/book?book=${encodeURIComponent(title)}`);
      if (!response.ok) throw new Error(`Error ${response.status}`);
      const books = await response.json();
      if (!books.length) {
        resultsContainer.innerHTML = `<div class="empty-message">No similar books found for "${title}"</div>`;
        return;
      }
      resultsContainer.innerHTML = "";

// In the book filter section of search.js, replace the card creation code with:
books.forEach(book => {
    const card = document.createElement("div");
    card.className = "book-card";

    // Create link wrapper
    const link = document.createElement("a");
    link.href = `/book/${book.key.replace("/works/","")}`;
    link.className = "book-link";

    // Cover image
    if (book.cover_id) {
        const img = document.createElement("img");
        img.src = `https://covers.openlibrary.org/b/id/${book.cover_id}-M.jpg`;
        img.alt = `Cover for ${book.title}`;
        img.className = "book-cover";
        img.loading = "lazy";
        link.appendChild(img);
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
