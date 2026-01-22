let allPlayers = [];
let filteredPlayers = [];
let leagueIds = [];
let leagueNames = {};  // Store league names

function addLeagueInput() {
    const container = document.getElementById('league-inputs');
    const newRow = document.createElement('div');
    newRow.className = 'league-input-row';
    newRow.innerHTML = `
        <input type="text" class="league-id" placeholder="Enter 18-digit League ID (e.g., 123456789012)" />
        <button class="btn-remove" onclick="removeLeagueInput(this)">
            <i class="fas fa-times"></i>
        </button>
    `;
    container.appendChild(newRow);
}

function removeLeagueInput(button) {
    const container = document.getElementById('league-inputs');
    if (container.children.length > 1) {
        button.parentElement.remove();
    }
}

async function fetchPlayers() {
    const username = document.getElementById('username').value.trim();
    if (!username) {
        showError('Please enter your Sleeper username');
        return;
    }

    // Get all league IDs
    const leagueInputs = document.querySelectorAll('.league-id');
    leagueIds = Array.from(leagueInputs)
        .map(input => input.value.trim())
        .filter(id => id !== '');

    if (leagueIds.length === 0) {
        showError('Please enter at least one League ID');
        return;
    }

    // Show loading
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('error-message').classList.add('hidden');
    document.getElementById('stats').classList.add('hidden');
    document.getElementById('filter-section').classList.add('hidden');
    document.getElementById('table-container').classList.add('hidden');

    try {
        const response = await fetch('/api/get-players', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                league_ids: leagueIds
            })
        });

        const data = await response.json();

        if (data.success) {
            allPlayers = data.players;
            filteredPlayers = [...allPlayers];
            leagueNames = data.league_names || {};  // Store league names
            displayPlayers();
            updateStats();
            populateFilters();
            
            // Show UI elements
            document.getElementById('stats').classList.remove('hidden');
            document.getElementById('filter-section').classList.remove('hidden');
            document.getElementById('table-container').classList.remove('hidden');
        } else {
            showError(data.error || 'Failed to fetch player data');
        }
    } catch (error) {
        showError('Error connecting to server: ' + error.message);
    } finally {
        document.getElementById('loading').classList.add('hidden');
    }
}

function populateFilters() {
    // Populate team filter
    const teamFilter = document.getElementById('team-filter');
    const teams = [...new Set(allPlayers.map(p => p.team))].filter(t => t).sort();
    teamFilter.innerHTML = '<option value="">All</option>';
    teams.forEach(team => {
        const option = document.createElement('option');
        option.value = team;
        option.textContent = team;
        teamFilter.appendChild(option);
    });

    // Populate college filter
    const collegeFilter = document.getElementById('college-filter');
    const colleges = [...new Set(allPlayers.map(p => p.college))].filter(c => c).sort();
    collegeFilter.innerHTML = '<option value="">All</option>';
    colleges.forEach(college => {
        const option = document.createElement('option');
        option.value = college;
        option.textContent = college;
        collegeFilter.appendChild(option);
    });
}

function displayPlayers() {
    const tableHeaders = document.getElementById('table-headers');
    const tableBody = document.getElementById('table-body');

    // Clear existing content
    tableHeaders.innerHTML = '';
    tableBody.innerHTML = '';

    if (filteredPlayers.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="100" style="text-align: center; padding: 30px;">No players found</td></tr>';
        return;
    }

    // Generate headers
    const baseHeaders = [
        'Name', 'Position', 'Team', 'Experience (yrs)', 'Height', 'Weight (lbs)', 
        'College', 'Age', 'Birthdate', 'NFL Career Snaps', 'Overall Rank', 'Position Rank', 'RAS Score',
        'FA Year', 'FA Type', 'Draft Year', 'Draft Round', 'Draft Pick'
    ];

    // Add league headers with names
    leagueIds.forEach(leagueId => {
        const leagueName = leagueNames[leagueId] || `League ${leagueId}`;
        baseHeaders.push(leagueName);
    });

    baseHeaders.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header;
        tableHeaders.appendChild(th);
    });

    // Generate rows
    filteredPlayers.forEach(player => {
        const row = document.createElement('tr');

        const cells = [
            player.name,
            player.position,
            player.team || 'FA',
            player.experience || '',
            player.height || '',  // Now formatted as feet'inches\"
            player.weight || '',
            player.college || '',
            player.age || '',
            player.birthdate || '',
            player.nfl_career_snaps || '',  // New snap counts column
            player.overall_rank || '',
            player.position_rank || '',
            player.ras_score || '',
            player.free_agency_year || '',
            player.free_agency_type || '',
            player.draft_year || '',
            player.draft_round || '',
            player.draft_pick || ''
        ];

        // Add league ownership data
        leagueIds.forEach(leagueId => {
            const ownership = player[`league_${leagueId}`] || '';
            cells.push(ownership);
        });

        cells.forEach((cellData, index) => {
            const td = document.createElement('td');
            td.textContent = cellData;

            // Style ownership columns (now starting at index 18 due to new snap counts column)
            if (index >= 18) { // League columns start at index 18
                if (cellData === 'Owned') {
                    td.className = 'ownership-owned';
                } else if (cellData === 'Available') {
                    td.className = 'ownership-available';
                } else if (cellData && cellData.includes('Invalid')) {
                    td.className = 'ownership-error';
                    td.title = 'Please check your League ID - it should be 18+ digits from your Sleeper league URL';
                } else if (cellData === 'Invalid Username') {
                    td.className = 'ownership-error';
                    td.title = 'Username not found - please check your Sleeper username';
                } else if (cellData === 'Error') {
                    td.className = 'ownership-error';
                } else if (cellData && cellData !== 'Error') {
                    td.className = 'ownership-other';
                }
            }

            row.appendChild(td);
        });

        tableBody.appendChild(row);
    });
}

function updateStats() {
    document.getElementById('total-players').textContent = allPlayers.length;

    const qbs = allPlayers.filter(p => p.position === 'QB').length;
    const rbs = allPlayers.filter(p => p.position === 'RB').length;
    const wrs = allPlayers.filter(p => p.position === 'WR').length;
    const tes = allPlayers.filter(p => p.position === 'TE').length;

    document.getElementById('qb-count').textContent = qbs;
    document.getElementById('rb-count').textContent = rbs;
    document.getElementById('wr-count').textContent = wrs;
    document.getElementById('te-count').textContent = tes;
}

function applyFilters() {
    const positionFilter = document.getElementById('position-filter').value;
    const teamFilter = document.getElementById('team-filter').value;
    const collegeFilter = document.getElementById('college-filter').value;
    const searchFilter = document.getElementById('search-filter').value.toLowerCase();
    
    // Age range filters
    const minAge = document.getElementById('min-age').value;
    const maxAge = document.getElementById('max-age').value;
    
    // Experience range filters
    const minExp = document.getElementById('min-experience').value;
    const maxExp = document.getElementById('max-experience').value;

    filteredPlayers = allPlayers.filter(player => {
        const matchPosition = !positionFilter || player.position === positionFilter;
        const matchTeam = !teamFilter || player.team === teamFilter;
        const matchCollege = !collegeFilter || player.college === collegeFilter;
        const matchSearch = !searchFilter || player.name.toLowerCase().includes(searchFilter);
        
        // Age range check
        const playerAge = player.age || 0;
        const matchMinAge = !minAge || playerAge >= parseInt(minAge);
        const matchMaxAge = !maxAge || playerAge <= parseInt(maxAge);
        
        // Experience range check
        const playerExp = player.experience || 0;
        const matchMinExp = !minExp || playerExp >= parseInt(minExp);
        const matchMaxExp = !maxExp || playerExp <= parseInt(maxExp);

        return matchPosition && matchTeam && matchCollege && matchSearch && 
               matchMinAge && matchMaxAge && matchMinExp && matchMaxExp;
    });

    displayPlayers();
    
    // Update filtered count if element exists
    const filteredCountEl = document.getElementById('filtered-count');
    if (filteredCountEl) {
        filteredCountEl.textContent = filteredPlayers.length;
    }
}

function clearFilters() {
    document.getElementById('position-filter').value = '';
    document.getElementById('team-filter').value = '';
    if (document.getElementById('college-filter')) document.getElementById('college-filter').value = '';
    document.getElementById('search-filter').value = '';
    if (document.getElementById('min-age')) document.getElementById('min-age').value = '';
    if (document.getElementById('max-age')) document.getElementById('max-age').value = '';
    if (document.getElementById('min-experience')) document.getElementById('min-experience').value = '';
    if (document.getElementById('max-experience')) document.getElementById('max-experience').value = '';
    filteredPlayers = [...allPlayers];
    displayPlayers();
    const filteredCountEl = document.getElementById('filtered-count');
    if (filteredCountEl) {
        filteredCountEl.textContent = filteredPlayers.length;
    }
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

// Add event listeners for real-time filtering
document.getElementById('position-filter').addEventListener('change', applyFilters);
document.getElementById('team-filter').addEventListener('change', applyFilters);
document.getElementById('search-filter').addEventListener('input', applyFilters);

// Add event listeners for new filters (with null checks)
if (document.getElementById('college-filter')) {
    document.getElementById('college-filter').addEventListener('change', applyFilters);
}
if (document.getElementById('min-age')) {
    document.getElementById('min-age').addEventListener('input', applyFilters);
}
if (document.getElementById('max-age')) {
    document.getElementById('max-age').addEventListener('input', applyFilters);
}
if (document.getElementById('min-experience')) {
    document.getElementById('min-experience').addEventListener('input', applyFilters);
}
if (document.getElementById('max-experience')) {
    document.getElementById('max-experience').addEventListener('input', applyFilters);
}
