document.addEventListener("DOMContentLoaded", async () => {
    /**
 * Load and display book details and recommended books on the book detail page.
 *
 * This script executes when the DOM is fully loaded and performs the following steps:
 * 1. Extracts the book's work key from the current URL path.
 * 2. Shows loading placeholders for both the book detail section and recommendations.
 * 3. Sends a request to `/api/book/{workKey}?limit=5` to retrieve:
 *    - Detailed metadata for the book (title, authors, rating, subjects, description, cover).
 *    - A list of recommended similar books.
 * 4. Renders the book information and its metadata in the `#book-detail` element.
 * 5. Renders up to 5 book recommendations as clickable cards with title, author(s), and cover.
 * 6. Displays appropriate fallback messages when no data is available or if an error occurs.
 */

  const detailEl = document.getElementById("book-detail");
  const recEl = document.getElementById("recommendations");
  const parts = window.location.pathname.split("/");
  const workKey = parts[parts.length - 1];

  detailEl.innerHTML = "<div class='loading'>Loading book details...</div>";
  recEl.innerHTML = "<div class='loading'>Loading recommendations...</div>";

  try {
    const resp = await fetch(`/api/book/${workKey}?limit=5`);
    if (!resp.ok) throw new Error(resp.statusText);
    const { detail, recommendations } = await resp.json();

    // Build detail panel
    let html = `
      <h1 class="book-title">${detail.title}</h1>
      <div class="book-meta-container">
        ${detail.authors.length ? `
          <div class="book-meta">
            <strong>Author:</strong> ${detail.authors.join(", ")}
          </div>
        ` : ''}
        ${detail.rating ? `
          <div class="book-meta">
            <strong>Rating:</strong> ${detail.rating.toFixed(1)} (${detail.rating_count || 0} reviews)
          </div>
        ` : ''}
        ${detail.subjects?.length ? `
          <div class="book-meta">
            <strong>Genres:</strong> ${detail.subjects.slice(0, 5).join(", ")}
          </div>
        ` : ''}
      </div>
      <div class="book-content">
        ${detail.covers?.length ? `
          <div class="book-cover-container">
            <img src="https://covers.openlibrary.org/b/id/${detail.covers[0]}-L.jpg"
                 alt="Cover for ${detail.title}" class="book-cover">
          </div>
        ` : ''}
        <div class="book-description">
          <h3>Description</h3>
          <p>${detail.description || 'No description available.'}</p>
        </div>
      </div>
    `;
    detailEl.innerHTML = html;

    // Build recommendation list
    if (recommendations.length) {
      let recHtml = recommendations.map(b => `
        <div class="recommendation-card">
          <a href="/book/${b.key.replace("/works/","")}">
            ${b.cover_id ?
              `<img src="https://covers.openlibrary.org/b/id/${b.cover_id}-M.jpg"
                   alt="${b.title}" class="rec-cover">` : ''}
            <h4>${b.title}</h4>
            <p>${b.authors?.join(", ") || "Unknown author"}</p>
          </a>
        </div>
      `).join('');
      recEl.innerHTML = recHtml;
    } else {
      recEl.innerHTML = '<p>No recommendations found</p>';
    }

  } catch (err) {
    detailEl.innerHTML = `<p class="error">Failed to load: ${err.message}</p>`;
    recEl.innerHTML = "";
  }
});