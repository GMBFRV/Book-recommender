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

    out.innerHTML = '<div class="loading-message">Searching for books...</div>';

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

        out.appendChild(card);
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

                // Display results
                authorResults.innerHTML = `
                    <h3>Authors similar to ${authorName}:</h3>
                    <div class="authors-grid">
                    ${authors.map(author => `
                        <div class="author-card">
                        <h4>${author.name}</h4>
                        ${author.top_work ? `<p class="author-work">Known for: ${author.top_work}</p>` : ''}
                        ${author.rating ? `<p class="author-rating">Avg rating: ${author.rating.toFixed(1)}</p>` : ''}
                        ${author.works_count ? `<p class="author-count">Works: ${author.works_count}</p>` : ''}
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

      books.forEach(book => {
        const card = document.createElement("div");
        card.className = "book-card";

        // Cover image
        if (book.cover_id) {
          const img = document.createElement("img");
          img.src = `https://covers.openlibrary.org/b/id/${book.cover_id}-M.jpg`;
          img.alt = `Cover for ${book.title}`;
          img.className = "book-cover";
          card.appendChild(img);
        }

        const info = document.createElement("div");
        info.className = "book-info";

        // Title
        const h3 = document.createElement("h3");
        h3.textContent = book.title || "No title available";
        info.appendChild(h3);

        // Authors
        const pAuthor = document.createElement("p");
        pAuthor.textContent = (book.authors || book.author_name || []).join(", ") || "Unknown author";
        pAuthor.className = "book-authors";
        info.appendChild(pAuthor);

        // Rating and reviews
        const pRating = document.createElement("p");
        const rating = book.rating ?? book.ratings_average ?? 0;
        const count = book.rating_count ?? book.ratings_count ?? 0;
        pRating.textContent = `Rating: ${rating.toFixed(1)} (${count} reviews)`;
        pRating.className = "book-rating";
        info.appendChild(pRating);

        card.appendChild(info);
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
