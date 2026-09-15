import React, { useState } from 'react';
import { generateAndDownloadDocument } from '../api/documentService';

export default function RetainerForm() {
  // 1. Hold form values in React state
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    service_type: 'Legal Representation',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // 2. Update state when the user types in any input
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  // 3. Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Pass the dynamic form data to your API helper
      await generateAndDownloadDocument(formData);
    } catch (err) {
      setError(err.message || 'Failed to download document.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '400px', margin: '2rem auto', padding: '1rem', border: '1px solid #ccc' }}>
      <h2>Generate Legal Retainer</h2>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <label>Full Name:</label>
          <input
            type="text"
            name="full_name"
            value={formData.full_name}
            onChange={handleChange}
            required
            style={{ width: '100%', padding: '8px' }}
          />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label>Email Address:</label>
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
            style={{ width: '100%', padding: '8px' }}
          />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label>Phone Number:</label>
          <input
            type="text"
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            required
            style={{ width: '100%', padding: '8px' }}
          />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label>Service Type:</label>
          <select
            name="service_type"
            value={formData.service_type}
            onChange={handleChange}
            style={{ width: '100%', padding: '8px' }}
          >
            <option value="Legal Representation">Legal Representation</option>
            <option value="Corporate Advisory">Corporate Advisory</option>
            <option value="Conveyance & Property">Conveyance & Property</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{ width: '100%', padding: '10px', backgroundColor: '#0f172a', color: '#fff', cursor: 'pointer' }}
        >
          {loading ? 'Generating Word Document...' : 'Download Retainer (.docx)'}
        </button>
      </form>
    </div>
  );
}