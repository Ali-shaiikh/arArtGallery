import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import '../css/Seller.css';

const API_BASE = '';

function capitalizeFirst(str) {
  if (!str) return '';
  return str.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
}

export default function Seller() {
  const [artworks, setArtworks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createStatus, setCreateStatus] = useState({ type: '', msg: '' });
  const [listStatus, setListStatus] = useState({ type: '', msg: '' });
  const [editModal, setEditModal] = useState(null);
  const [editStatus, setEditStatus] = useState({ type: '', msg: '' });
  const [submitting, setSubmitting] = useState(false);

  const showMessage = (setter, msg, type) => {
    setter({ type, msg });
    setTimeout(() => setter({ type: '', msg: '' }), 5000);
  };

  // ✅ Seller should load only THEIR artworks
  const loadArtworks = () => {
    setLoading(true);

    // changed from /artworks -> /seller/artworks
    const url = `${API_BASE}/seller/artworks`.replace(/\/+/, '/') || '/seller/artworks';

    fetch(url, { credentials: 'include' })
      .then(async (res) => {
        const text = await res.text();
        if (!res.ok) throw new Error(text || `Failed to load artworks (${res.status})`);
        return text ? JSON.parse(text) : [];
      })
      .then((data) => {
        setArtworks(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch((err) => {
        setListStatus({ type: 'error', msg: err.message || 'Failed to load artworks' });
        setLoading(false);
      });
  };

  useEffect(() => loadArtworks(), []);

  const handleCreate = async (e) => {
    e.preventDefault();
    const form = e.target;
    const fileInput = form.image;

    if (!fileInput?.files?.[0]) {
      showMessage(setCreateStatus, 'Please select an image file', 'error');
      return;
    }

    const name = form.name.value.trim();
    if (!name) {
      showMessage(setCreateStatus, 'Artwork name is required', 'error');
      return;
    }

    setSubmitting(true);

    const formData = new FormData();
    formData.append('image', fileInput.files[0]);
    formData.append('name', name);
    formData.append('description', form.description?.value?.trim() || '');
    formData.append('price', form.price?.value || '');
    formData.append('artwork_type', form.artwork_type?.value || '');
    formData.append('artist', form.artist?.value?.trim() || '');
    formData.append('year_created', form.year_created?.value || '');
    formData.append('dimensions', form.dimensions?.value?.trim() || '');
    formData.append('medium', form.medium?.value || '');
    formData.append('style', form.style?.value || '');

    try {
      const res = await fetch(`${API_BASE}/make-glb`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || 'Failed to create artwork');

      showMessage(setCreateStatus, 'Artwork created successfully!', 'success');
      form.reset();
      setShowCreate(false);

      // reload seller artworks
      loadArtworks();
    } catch (err) {
      showMessage(setCreateStatus, err.message, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!editModal) return;

    // ❌ safety: sold artwork edit not allowed
    if (editModal.is_sold) {
      showMessage(setEditStatus, 'This artwork is SOLD. You cannot edit it.', 'error');
      return;
    }

    const form = e.target;
    const name = form.editName.value.trim();

    if (!name) {
      showMessage(setEditStatus, 'Artwork name is required', 'error');
      return;
    }

    setSubmitting(true);

    const payload = {
      name,
      description: form.editDescription?.value?.trim() || '',
      price: form.editPrice?.value || null,
      artwork_type: form.editArtworkType?.value || '',
      artist: form.editArtist?.value?.trim() || '',
      year_created: form.editYearCreated?.value || null,
      dimensions: form.editDimensions?.value?.trim() || '',
      medium: form.editMedium?.value || '',
      style: form.editStyle?.value || '',
    };

    try {
      const res = await fetch(`${API_BASE}/api/artwork/${editModal.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || 'Failed to update');

      showMessage(setListStatus, 'Artwork updated successfully!', 'success');
      setEditModal(null);
      loadArtworks();
    } catch (err) {
      showMessage(setEditStatus, err.message, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id, name, isSold) => {
    // ❌ safety: sold artwork delete not allowed
    if (isSold) {
      showMessage(setListStatus, 'This artwork is SOLD. You cannot delete it.', 'error');
      return;
    }

    if (!window.confirm(`Are you sure you want to delete "${name}"? This cannot be undone.`)) return;

    try {
      const res = await fetch(`${API_BASE}/api/artwork/${id}`, {
        method: 'DELETE',
        credentials: 'include',
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || 'Failed to delete');

      showMessage(setListStatus, `"${name}" deleted successfully`, 'success');
      loadArtworks();
    } catch (err) {
      showMessage(setListStatus, err.message, 'error');
    }
  };

  const openEdit = (artwork) => {
    if (artwork.is_sold) {
      showMessage(setListStatus, 'This artwork is SOLD. You cannot edit it.', 'error');
      return;
    }
    setEditModal(artwork);
  };

  const closeEdit = () => setEditModal(null);

  const selectOptions = {
    artwork_type: ['', 'painting', 'sculpture', 'photography', 'digital', 'print', 'mixed_media', 'other'],
    medium: ['', 'oil', 'acrylic', 'watercolor', 'gouache', 'pastel', 'charcoal', 'pencil', 'ink', 'mixed_media', 'photography', 'digital', 'printmaking', 'other'],
    style: ['', 'abstract', 'realistic', 'impressionist', 'expressionist', 'surrealist', 'cubist', 'minimalist', 'pop_art', 'contemporary', 'modern', 'classical', 'other'],
  };

  return (
    <div className="seller-container">
      <header className="seller-header">
        <h1>🎨 Seller Dashboard</h1>
        <div className="header-actions">
          <button type="button" onClick={() => setShowCreate(true)}>+ New Artwork</button>
          <Link to="/select-role" className="btn-secondary">← Back</Link>
        </div>
      </header>

      <div className="main-content">
        <div className={`section create-form ${showCreate ? 'active' : ''}`}>
          <div className="section-title">Create New Artwork</div>
          {createStatus.msg && (
            <div className={`status-message ${createStatus.type}`}>{createStatus.msg}</div>
          )}
          <form onSubmit={handleCreate}>
            <div className="form-group">
              <label htmlFor="imageFile">Artwork Image *</label>
              <input type="file" id="imageFile" name="image" accept="image/*" required />
            </div>

            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="name">Artwork Name *</label>
                <input type="text" id="name" name="name" placeholder="Enter artwork name" required />
              </div>

              <div className="form-group">
                <label htmlFor="artist">Artist</label>
                <input type="text" id="artist" name="artist" placeholder="Artist name" />
              </div>

              <div className="form-group">
                <label htmlFor="price">Price ($)</label>
                <input type="number" id="price" name="price" placeholder="0.00" step="0.01" min="0" />
              </div>

              <div className="form-group">
                <label htmlFor="artwork_type">Type</label>
                <select id="artwork_type" name="artwork_type">
                  <option value="">Select type</option>
                  {selectOptions.artwork_type.filter(Boolean).map((v) => (
                    <option key={v} value={v}>{capitalizeFirst(v)}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="year_created">Year Created</label>
                <input type="number" id="year_created" name="year_created" placeholder="2025" min="1900" max="2025" />
              </div>

              <div className="form-group">
                <label htmlFor="medium">Medium</label>
                <select id="medium" name="medium">
                  <option value="">Select medium</option>
                  {selectOptions.medium.filter(Boolean).map((v) => (
                    <option key={v} value={v}>{capitalizeFirst(v)}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="dimensions">Dimensions</label>
                <input type="text" id="dimensions" name="dimensions" placeholder="e.g., 24x36 inches" />
              </div>

              <div className="form-group">
                <label htmlFor="style">Style</label>
                <select id="style" name="style">
                  <option value="">Select style</option>
                  {selectOptions.style.filter(Boolean).map((v) => (
                    <option key={v} value={v}>{capitalizeFirst(v)}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="description">Description</label>
              <textarea id="description" name="description" placeholder="Describe your artwork..." />
            </div>

            <div className="form-actions">
              <button type="submit" disabled={submitting}>
                {submitting ? 'Creating...' : 'Create Artwork'}
              </button>
              <button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>
                Cancel
              </button>
            </div>
          </form>
        </div>

        <div className="section">
          <div className="section-title">My Artworks</div>

          {listStatus.msg && (
            <div className={`status-message ${listStatus.type}`}>{listStatus.msg}</div>
          )}

          {loading ? (
            <div className="loading">Loading artworks...</div>
          ) : artworks.length === 0 ? (
            <div className="empty-state">
              <h3>No artworks yet</h3>
              <p>Click &quot;New Artwork&quot; to create your first piece</p>
            </div>
          ) : (
            <div className="artworks-grid">
              {artworks.map((artwork) => (
                <div key={artwork.id} className="artwork-card">
                  <img
                    src={`${API_BASE}/artwork/${artwork.id}/image`}
                    alt={artwork.name}
                    className="artwork-image"
                  />

                  <div className="artwork-details">
                    <div className="artwork-name">
                      {artwork.name}

                      {/* ✅ SOLD badge */}
                      {artwork.is_sold && (
                        <span
                          style={{
                            marginLeft: '10px',
                            padding: '4px 10px',
                            borderRadius: '999px',
                            fontSize: '12px',
                            fontWeight: '700',
                            background: '#ff4d4f',
                            color: 'white',
                          }}
                        >
                          SOLD
                        </span>
                      )}
                    </div>

                    {artwork.artist && <div className="artwork-info">🎨 {artwork.artist}</div>}
                    {artwork.artwork_type && (
                      <div className="artwork-info">📦 {capitalizeFirst(artwork.artwork_type)}</div>
                    )}
                    {artwork.year_created && <div className="artwork-info">📅 {artwork.year_created}</div>}
                    {artwork.dimensions && <div className="artwork-info">📏 {artwork.dimensions}</div>}
                    {artwork.price != null && (
                      <div className="artwork-price">${Number(artwork.price).toFixed(2)}</div>
                    )}

                    <div className="artwork-actions">
                      <button
                        type="button"
                        className="btn-secondary btn-small"
                        onClick={() => openEdit(artwork)}
                        disabled={artwork.is_sold}
                        title={artwork.is_sold ? 'Sold artworks cannot be edited' : 'Edit'}
                      >
                        Edit
                      </button>

                      <button
                        type="button"
                        className="btn-danger btn-small"
                        onClick={() => handleDelete(artwork.id, artwork.name, artwork.is_sold)}
                        disabled={artwork.is_sold}
                        title={artwork.is_sold ? 'Sold artworks cannot be deleted' : 'Delete'}
                      >
                        Delete
                      </button>
                    </div>

                    {/* ✅ Sold message */}
                    {artwork.is_sold && (
                      <div style={{ marginTop: '8px', fontSize: '13px', fontWeight: '600', color: '#ff4d4f' }}>
                        ✅ This artwork has been sold
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {editModal && (
        <div className="modal active" onClick={(e) => e.target === e.currentTarget && closeEdit()}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Edit Artwork</h2>
              <button type="button" className="close-modal" onClick={closeEdit}>&times;</button>
            </div>

            {editStatus.msg && (
              <div className={`status-message ${editStatus.type}`}>{editStatus.msg}</div>
            )}

            <form onSubmit={handleUpdate}>
              <div className="form-grid">
                <div className="form-group">
                  <label htmlFor="editName">Artwork Name *</label>
                  <input type="text" id="editName" name="editName" defaultValue={editModal.name} required />
                </div>

                <div className="form-group">
                  <label htmlFor="editArtist">Artist</label>
                  <input type="text" id="editArtist" name="editArtist" defaultValue={editModal.artist} />
                </div>

                <div className="form-group">
                  <label htmlFor="editPrice">Price ($)</label>
                  <input type="number" id="editPrice" name="editPrice" step="0.01" min="0" defaultValue={editModal.price} />
                </div>

                <div className="form-group">
                  <label htmlFor="editArtworkType">Type</label>
                  <select id="editArtworkType" name="editArtworkType" defaultValue={editModal.artwork_type}>
                    <option value="">Select type</option>
                    {selectOptions.artwork_type.filter(Boolean).map((v) => (
                      <option key={v} value={v}>{capitalizeFirst(v)}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="editYearCreated">Year Created</label>
                  <input type="number" id="editYearCreated" name="editYearCreated" min="1900" max="2025" defaultValue={editModal.year_created} />
                </div>

                <div className="form-group">
                  <label htmlFor="editMedium">Medium</label>
                  <select id="editMedium" name="editMedium" defaultValue={editModal.medium}>
                    <option value="">Select medium</option>
                    {selectOptions.medium.filter(Boolean).map((v) => (
                      <option key={v} value={v}>{capitalizeFirst(v)}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="editDimensions">Dimensions</label>
                  <input type="text" id="editDimensions" name="editDimensions" defaultValue={editModal.dimensions} />
                </div>

                <div className="form-group">
                  <label htmlFor="editStyle">Style</label>
                  <select id="editStyle" name="editStyle" defaultValue={editModal.style}>
                    <option value="">Select style</option>
                    {selectOptions.style.filter(Boolean).map((v) => (
                      <option key={v} value={v}>{capitalizeFirst(v)}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="editDescription">Description</label>
                <textarea id="editDescription" name="editDescription" defaultValue={editModal.description} />
              </div>

              <div className="form-actions">
                <button type="submit" disabled={submitting}>
                  {submitting ? 'Updating...' : 'Update Artwork'}
                </button>
                <button type="button" className="btn-secondary" onClick={closeEdit}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
