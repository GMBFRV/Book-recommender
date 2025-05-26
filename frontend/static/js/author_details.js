document.addEventListener("DOMContentLoaded", async () => {
  /**
 * Load and display author details and their works when the author page is opened.
 *
 * This script runs after the DOM is fully loaded. It performs the following steps:
 * 1. Extracts the author's key from the URL path.
 * 2. Displays loading indicators in the author and books sections.
 * 3. Fetches the author's metadata from `/api/author/{authorKey}` and renders:
 *    - Name, photo, birth/death dates, works count, rating, and biography.
 * 4. Fetches the author's books from `/api/author/{authorKey}/works?languages=en,ru` and renders:
 *    - Book cover, title, and rating (if available).
 * 5. Handles missing data (e.g., no photo or books) with placeholders and fallback messages.
 * 6. Catches and displays any errors that occur during the fetch process.
 */

  const authorEl = document.getElementById("author-detail");
  const booksEl = document.getElementById("author-books");
  const parts = window.location.pathname.split("/");
  const authorKey = parts[parts.length - 1];

  // Loading states
  authorEl.innerHTML = `
    <div class="loading">
      <div class="loading-spinner"></div>
      <div class="loading-message">Loading author details...</div>
    </div>
  `;
  booksEl.innerHTML = `
    <div class="loading">
      <div class="loading-spinner"></div>
      <div class="loading-message">Loading author's books...</div>
    </div>
  `;

  try {
    // Fetch author details
    const authorResp = await fetch(`/api/author/${authorKey}`);
    if (!authorResp.ok) throw new Error(authorResp.statusText);
    const author = await authorResp.json();

    // Build author detail panel
    let html = `
      <div class="author-header">
        <div class="author-photo-container">
          ${author.photo_id
            ? `<img 
                src="https://covers.openlibrary.org/a/olid/${author.key}-L.jpg" 
                alt="${author.name}" 
                class="author-photo-large">`
            : `<img 
                src="/static/images/no-photo-author.jpg" 
                alt="Default Author" 
                class="author-photo-large placeholder">`
          }
        </div>
        <div class="author-info">
          <h1 class="author-name">${author.name}</h1>
          
          <div class="author-meta">
            ${author.birth_date ? `<p><strong>Born:</strong> ${author.birth_date}</p>` : ''}
            ${author.death_date ? `<p><strong>Died:</strong> ${author.death_date}</p>` : ''}
            ${author.works_count ? `<p><strong>Works:</strong> ${author.works_count}</p>` : ''}
            ${author.rating ? `<p><strong>Average Rating:</strong> ${author.rating.toFixed(1)}</p>` : ''}
          </div>
        </div>
      </div>
      
      ${author.bio ? `
        <div class="author-bio">
          <h3>Biography</h3>
          <p>${author.bio}</p>
        </div>
      ` : ''}
    `;
    authorEl.innerHTML = html;

    // Fetch author's books
    const booksResp = await fetch(`/api/author/${authorKey}/works?languages=en,ru`);
    if (!booksResp.ok) throw new Error(booksResp.statusText);
    const books = await booksResp.json();

    // Build books list
    if (books.length) {
      let booksHtml = books.map(b => `
        <div class="book-card">
          <a href="/book/${b.key.replace("/works/","")}">
            ${b.cover_id
              ? `<img
                   src="https://covers.openlibrary.org/b/id/${b.cover_id}-M.jpg"
                    alt="${b.title}"
                    class="book-cover">`
              : `<img
                   src="/static/images/no-cover-photo.jpg"
                    alt="Default cover"
                    class="book-cover placeholder">`
            }
            <div class="book-info">
              <h4>${b.title}</h4>
              ${b.rating ? `<p class="book-rating">★ ${b.rating.toFixed(1)}</p>` : ''}
            </div>
          </a>
        </div>
      `).join('');
      booksEl.innerHTML = booksHtml;
    } else {
      booksEl.innerHTML = '<p class="empty-message">No books found for this author</p>';
    }

  } catch (err) {
    authorEl.innerHTML = `<p class="error-message">Failed to load: ${err.message}</p>`;
    booksEl.innerHTML = "";
  }
});