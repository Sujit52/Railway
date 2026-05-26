const csvFiles = ['1.csv', '2.csv', '3.csv', '4.csv', '5.csv'];
let allData = []; // { filename, records }

async function loadAllCSV() {
    allData = [];
    const loadingDiv = document.getElementById('loading');
    loadingDiv.style.display = 'block';

    for (let file of csvFiles) {
        try {
            const response = await fetch(file);
            const csvText = await response.text();
            const parsed = Papa.parse(csvText, { header: true, skipEmptyLines: true });
            if (parsed.data && parsed.data.length) {
                allData.push({
                    filename: file,
                    records: parsed.data
                });
            }
        } catch (err) {
            console.error(`Error loading ${file}:`, err);
        }
    }
    loadingDiv.style.display = 'none';
    document.getElementById('resultsCount').innerHTML = `✅ ${allData.reduce((acc, f) => acc + f.records.length, 0)} records loaded from ${allData.length} files. Start searching.`;
}

function searchInAllFiles(searchTerm) {
    if (!searchTerm || searchTerm.trim() === '') {
        document.getElementById('results').innerHTML = '';
        document.getElementById('resultsCount').innerHTML = allData.length ? `✅ ${allData.reduce((acc, f) => acc + f.records.length, 0)} records loaded. Type to search.` : '';
        return;
    }

    const term = searchTerm.trim().toLowerCase();
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
            resultsHTML += `<div class="file-card">
                <div class="file-name">📁 ${fileData.filename} (${matchedRecords.length} matches)</div>
                <table>
                    <thead>
                        <tr><th>Certificate_No</th><th>Issue_Date_Input</th><th>Application_ID</th><th>Applicant_Name</th><th>Sex</th><th>Father_Name</th><th>Address</th><th>Caste</th><th>Sub_Caste</th><th>Issue_Date</th><th>Is_Valid</th><th>Issued_By</th></tr>
                    </thead>
                    <tbody>`;
            for (let rec of matchedRecords) {
                resultsHTML += `<tr>
                    <td>${rec.Certificate_No || ''}</td>
                    <td>${rec.Issue_Date_Input || ''}</td>
                    <td>${rec.Application_ID || ''}</td>
                    <td>${rec.Applicant_Name || ''}</td>
                    <td>${rec.Sex || ''}</td>
                    <td>${rec.Father_Name || ''}</td>
                    <td>${rec.Address || ''}</td>
                    <td>${rec.Caste || ''}</td>
                    <td>${rec.Sub_Caste || ''}</td>
                    <td>${rec.Issue_Date || ''}</td>
                    <td>${rec.Is_Valid || ''}</td>
                    <td>${rec.Issued_By || ''}</td>
                </tr>`;
            }
            resultsHTML += `</tbody></table></div>`;
        }
    }

    document.getElementById('resultsCount').innerHTML = `🔍 ${totalMatches} result(s) found for "${searchTerm.trim()}"`;
    document.getElementById('results').innerHTML = resultsHTML || `<div class="no-results">❌ No matching records found.</div>`;
}

// Debounce for fast typing
let debounceTimer;
document.getElementById('searchInput').addEventListener('input', function(e) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        searchInAllFiles(e.target.value);
    }, 300);
});

// Load all CSVs on page load
loadAllCSV();
