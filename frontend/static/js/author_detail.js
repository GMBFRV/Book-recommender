document.addEventListener("DOMContentLoaded", async () => {
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
          ${author.photo_id ? 
            `<img src="https://covers.openlibrary.org/a/olid/${author.key}-L.jpg" 
                  alt="${author.name}" class="author-photo-large">` : 
            '<div class="author-photo-large placeholder"></div>'}
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
    const booksResp = await fetch(`/api/author/${authorKey}/works`);
    if (!booksResp.ok) throw new Error(booksResp.statusText);
    const books = await booksResp.json();

    // Build books list
    if (books.length) {
      let booksHtml = books.map(book => `
        <div class="book-card">
          <a href="/book/${book.key.replace("/works/","")}">
            ${book.cover_id ?
              `<img src="https://covers.openlibrary.org/b/id/${book.cover_id}-M.jpg"
                   alt="${book.title}" class="book-cover">` : 
              '<div class="book-cover placeholder"></div>'}
            <div class="book-info">
              <h4>${book.title}</h4>
              ${book.rating ? `<p class="book-rating">★ ${book.rating.toFixed(1)}</p>` : ''}
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