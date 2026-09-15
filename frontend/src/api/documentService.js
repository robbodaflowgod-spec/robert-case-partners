/**
 * Sends form data to FastAPI, converts the binary response to a Blob,
 * and triggers an automated browser file download.
 *
 * @param {Object} formData - The client/contract data to populate in the document.
 */
export const generateAndDownloadDocument = async (formData) => {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  try {
   // Replace this line:
// const response = await fetch(`${API_BASE_URL}/api/documents/generate`, {

// With this:
const response = await fetch(`${API_BASE_URL}/documents/generate-retainer`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(formData),
});

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(errorData?.detail || `Server error: ${response.status}`);
    }

    // 1. Extract filename from response header (falls back if missing)
    let filename = 'Generated_Document.docx';
    const disposition = response.headers.get('Content-Disposition');
    if (disposition && disposition.includes('filename=')) {
      filename = disposition
        .split('filename=')[1]
        .replace(/["']/g, '') // remove surrounding quotes
        .trim();
    }

    // 2. Convert binary response to a browser Blob
    const blob = await response.blob();

    // 3. Create a temporary in-memory URL for the Blob
    const downloadUrl = window.URL.createObjectURL(blob);

    // 4. Create an invisible <a> element and trigger click
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();

    // 5. Clean up memory and remove temporary DOM element
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);

    return { success: true, filename };
  } catch (error) {
    console.error('Failed to generate document:', error);
    throw error;
  }
};