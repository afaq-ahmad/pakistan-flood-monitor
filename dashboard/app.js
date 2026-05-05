document.addEventListener('DOMContentLoaded', () => {
    // Initialize Map
    // Coordinates for Pakistan
    const map = L.map('map').setView([30.3753, 69.3451], 5);
    
    // Dark theme map tiles (CartoDB Dark Matter)
    const tiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    let markers = [];

    // View Navigation Logic
    const navLinks = document.querySelectorAll('#nav-links li');
    const viewSections = document.querySelectorAll('.view-section');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Remove active class from all links and views
            navLinks.forEach(l => l.classList.remove('active'));
            viewSections.forEach(v => v.classList.remove('active'));
            
            // Add active class to clicked link
            link.classList.add('active');
            
            // Show corresponding view
            const targetId = link.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');

            // Handle Leaflet map resize bug when becoming visible
            if (targetId === 'view-overview') {
                setTimeout(() => { map.invalidateSize(); }, 100);
            }
        });
    });

    // Map style switcher
    document.getElementById('map-style').addEventListener('change', (e) => {
        const style = e.target.value;
        let url = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
        if (style === 'satellite') {
            url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
        } else if (style === 'street') {
            url = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
        }
        tiles.setUrl(url);
    });

    // Fetch and render data
    async function fetchEvents() {
        try {
            const response = await fetch('/api/events');
            const result = await response.json();
            
            if (result.status === 'success') {
                renderDashboard(result.data);
            } else {
                showError(result.message);
            }
        } catch (error) {
            console.error('Error fetching data:', error);
            showError('Failed to load data from server.');
        }
    }

    function renderDashboard(data) {
        updateStats(data);
        updateTable(data);
        updateMap(data);
    }

    function updateStats(data) {
        let active = 0, critical = 0, pop = 0, confTotal = 0;
        
        data.forEach(row => {
            if (row.status === 'active') active++;
            if (row.severity === 'critical') critical++;
            pop += parseInt(row.affected_population || 0);
            confTotal += parseFloat(row.confidence || 0);
        });

        document.getElementById('stat-active').textContent = active;
        document.getElementById('stat-critical').textContent = critical;
        document.getElementById('stat-population').textContent = pop.toLocaleString();
        
        const avgConf = data.length ? Math.round((confTotal / data.length) * 100) : 0;
        document.getElementById('stat-confidence').textContent = `${avgConf}%`;
        document.getElementById('total-events').textContent = `${data.length} Total`;
    }

    function updateTable(data) {
        const tbody = document.getElementById('events-body');
        tbody.innerHTML = '';

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">No events found.</td></tr>';
            return;
        }

        data.forEach(row => {
            const tr = document.createElement('tr');
            
            const sevClass = row.severity ? row.severity.toLowerCase() : 'low';
            
            tr.innerHTML = `
                <td><strong>${row.event_id}</strong></td>
                <td><i class="fa-solid fa-location-dot" style="color:var(--text-secondary);margin-right:5px"></i> ${row.district}</td>
                <td><span class="status-badge ${sevClass}">${row.severity}</span></td>
                <td><span class="tag-badge">${row.status}</span></td>
                <td><button class="btn-small" onclick="focusMap(${row.latitude}, ${row.longitude})">View Map</button></td>
            `;
            tbody.appendChild(tr);
        });
    }

    function getSeverityColor(severity) {
        switch((severity || '').toLowerCase()) {
            case 'critical': return '#ef4444';
            case 'high': return '#f97316';
            case 'medium': return '#eab308';
            default: return '#3b82f6';
        }
    }

    function updateMap(data) {
        // Clear existing markers
        markers.forEach(m => map.removeLayer(m));
        markers = [];

        data.forEach(row => {
            if (row.latitude && row.longitude) {
                const color = getSeverityColor(row.severity);
                
                // Create a custom circle marker
                const marker = L.circleMarker([row.latitude, row.longitude], {
                    radius: 8,
                    fillColor: color,
                    color: '#fff',
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                }).addTo(map);

                const popupContent = `
                    <div class="popup-title">${row.event_id} - ${row.district}</div>
                    <div class="popup-row"><span class="popup-label">Severity:</span> <span class="popup-value" style="color:${color};text-transform:capitalize">${row.severity}</span></div>
                    <div class="popup-row"><span class="popup-label">Population at Risk:</span> <span class="popup-value">${parseInt(row.affected_population).toLocaleString()}</span></div>
                    <div class="popup-row"><span class="popup-label">Confidence:</span> <span class="popup-value">${Math.round(row.confidence * 100)}%</span></div>
                    <div class="popup-row"><span class="popup-label">Status:</span> <span class="popup-value" style="text-transform:capitalize">${row.status}</span></div>
                    <div class="popup-row"><span class="popup-label">Timestamp:</span> <span class="popup-value">${new Date(row.timestamp).toLocaleDateString()}</span></div>
                `;

                marker.bindPopup(popupContent);
                markers.push(marker);
            }
        });
        
        // Fit bounds to show all markers if any exist
        if (markers.length > 0) {
            const group = new L.featureGroup(markers);
            map.fitBounds(group.getBounds().pad(0.1));
        }
    }

    window.focusMap = function(lat, lng) {
        map.setView([lat, lng], 9, {
            animate: true,
            duration: 1
        });
    }

    function showError(msg) {
        document.getElementById('events-body').innerHTML = `<tr><td colspan="5" class="loading-cell"><i class="fa-solid fa-triangle-exclamation" style="color:var(--status-critical);font-size:24px;margin-bottom:10px;"></i><br>${msg}</td></tr>`;
    }

    // Refresh button logic
    document.getElementById('refresh-btn').addEventListener('click', () => {
        document.getElementById('events-body').innerHTML = '<tr><td colspan="5" class="loading-cell"><div class="spinner"></div><p>Refreshing data...</p></td></tr>';
        fetchEvents();
    });

    // Initial load
    fetchEvents();
});
