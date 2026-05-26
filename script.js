const csvFiles = ['1.csv', '2.csv', '3.csv', '4.csv', '5.csv'];
let allData = [];
let isSearching = false;

// Load all CSVs on page load
async function loadAllCSV() {
    const fileStatus = document.getElementById('fileStatus');
    fileStatus.innerHTML = '📁 Loading CSV files...';
    
    allData = [];
    
    for (let file of csvFiles) {
        try {
            const response = await fetch(file);
            const csvText = await response.text();
            const parsed = Papa.parse(csvText, { header: true, skipEmptyLines: true });
            
            if (parsed.data && parsed.data.length > 0) {
                // Remove any completely empty rows
                const validRecords = parsed.data.filter(row => 
                    row.Certificate_No && row.Certificate_No.trim() !== ''
                );
                
                if (validRecords.length > 0) {
                    allData.push({
                        filename: file,
                        records: validRecords
                    });
                }
            }
        } catch (err) {
            console.error(`Error loading ${file}:`, err);
        }
    }
    
    const totalRecords = allData.reduce((acc, f) => acc + f.records.length, 0);
    fileStatus.innerHTML = `✅ Loaded ${allData.length} files | 📄 ${totalRecords} total records`;
}

// Search function
function performSearch() {
    if (isSearching) return;
    
    const searchInput = document.getElementById('searchInput');
    const searchTerm = searchInput.value.trim();
    
    if (!searchTerm) {
        document.getElementById('results').innerHTML = '<div class="no-results">Please enter a search term</div>';
        document.getElementById('resultCount').innerHTML = '';
        return;
    }
    
    if (allData.length === 0) {
        document.getElementById('results').innerHTML = '<div class="no-results">No data loaded. Please refresh the page.</div>';
        return;
    }
    
    // Show loading overlay
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = 'flex';
    isSearching = true;
    
    // Small delay to show loading animation
    setTimeout(() => {
        try {
            const term = searchTerm.toLowerCase();
            let totalMatches = 0;
            let resultsHTML = '';
            
            for (let fileData of allData) {
                const matchedRecords = fileData.records.filter(record => {
                    return Object.values(record).some(value => 
                        value && value.toString().toLowerCase().includes(term)
                    );
                });
                
                if (matchedRecords.length > 0) {
                    totalMatches += matchedRecords.length;
                    
                    resultsHTML += `
                        <div class="file-card">
                            <div class="file-header">
                                <div class="file-name">📁 ${fileData.filename} — ${matchedRecords.length} match(es)</div>
                            </div>
                            <div class="table-wrapper">
                                <table class="data-table">
                                    <thead>
                                        <tr>
                                            <th>Certificate No</th>
                                            <th>Issue Date Input</th>
                                            <th>Application ID</th>
                                            <th>Applicant Name</th>
                                            <th>Sex</th>
                                            <th>Father's Name</th>
                                            <th>Address</th>
                                            <th>Caste</th>
                                            <th>Sub Caste</th>
                                            <th>Issue Date</th>
                                            <th>Is Valid</th>
                                            <th>Issued By</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                    `;
                    
                    for (let rec of matchedRecords) {
                        resultsHTML += `<tr>
                            <td>${escapeHtml(rec.Certificate_No || '-')}</td>
                            <td>${escapeHtml(rec.Issue_Date_Input || '-')}</td>
                            <td>${escapeHtml(rec.Application_ID || '-')}</td>
                            <td><strong>${escapeHtml(rec.Applicant_Name || '-')}</strong></td>
                            <td>${escapeHtml(rec.Sex || '-')}</td>
                            <td>${escapeHtml(rec.Father_Name || '-')}</td>
                            <td style="max-width: 200px; word-break: break-word;">${escapeHtml(rec.Address || '-')}</td>
                            <td>${escapeHtml(rec.Caste || '-')}</td>
                            <td>${escapeHtml(rec.Sub_Caste || '-')}</td>
                            <td>${escapeHtml(rec.Issue_Date || '-')}</td>
                            <td>${escapeHtml(rec.Is_Valid || '-')}</td>
                            <td>${escapeHtml(rec.Issued_By || '-')}</td>
                        </tr>`;
                    }
                    
                    resultsHTML += `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;
                }
            }
            
            // Update results
            const resultsDiv = document.getElementById('results');
            const resultCountSpan = document.getElementById('resultCount');
            
            if (totalMatches === 0) {
                resultsDiv.innerHTML = `<div class="no-results">No results found for "${escapeHtml(searchTerm)}"</div>`;
                resultCountSpan.innerHTML = `❌ 0 results`;
            } else {
                resultsDiv.innerHTML = resultsHTML;
                resultCountSpan.innerHTML = `🎯 ${totalMatches} result(s) found`;
            }
            
        } catch (error) {
            console.error('Search error:', error);
            document.getElementById('results').innerHTML = '<div class="no-results">Error occurred during search. Please try again.</div>';
        } finally {
            overlay.style.display = 'none';
            isSearching = false;
        }
    }, 100);
}

// Helper function to escape HTML
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Event Listeners
document.getElementById('searchBtn').addEventListener('click', performSearch);
document.getElementById('searchInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        performSearch();
    }
});

// Load data on page load
loadAllCSV();
