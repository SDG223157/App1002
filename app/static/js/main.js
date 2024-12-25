// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize form event listeners
    const analysisForm = document.getElementById('analysis-form');
    if (analysisForm) {
        analysisForm.addEventListener('submit', handleFormSubmit);
    }

    // Initialize input event listeners
    const lookbackInput = document.getElementById('lookback_days');
    const crossoverInput = document.getElementById('crossover_days');
    const tickerInput = document.getElementById('ticker');

    if (lookbackInput) {
        lookbackInput.addEventListener('input', handleLookbackInput);
    }
    if (crossoverInput) {
        crossoverInput.addEventListener('input', handleCrossoverInput);
    }
    if (tickerInput) {
        tickerInput.addEventListener('input', (e) => searchTicker(e.target.value));
    }

    // Initialize click listener for closing search results
    document.addEventListener('click', handleClickOutside);
});

// Form Submit Handler
function handleFormSubmit(event) {
    let lookbackDays = document.getElementById('lookback_days').value;
    let crossoverDays = document.getElementById('crossover_days').value;
    
    // Validate values
    lookbackDays = validateLookbackDays(lookbackDays);
    crossoverDays = validateCrossoverDays(crossoverDays);
    
    // Update form values
    document.getElementById('lookback_days').value = lookbackDays;
    document.getElementById('crossover_days').value = crossoverDays;
    
    console.log('Submitting form with values:', {
        ticker: document.getElementById('ticker').value,
        lookback_days: lookbackDays,
        crossover_days: crossoverDays,
        end_date: document.getElementById('end_date').value
    });
}

// Input Handlers
function handleLookbackInput(event) {
    let value = parseInt(event.target.value) || 365;
    event.target.value = validateLookbackDays(value);
    console.log('Lookback days updated to:', event.target.value);
}

function handleCrossoverInput(event) {
    let value = parseInt(event.target.value) || 365;
    event.target.value = validateCrossoverDays(value);
    console.log('Crossover days updated to:', event.target.value);
}

// Validation Functions
function validateLookbackDays(value) {
    value = parseInt(value) || 365;
    return Math.max(30, Math.min(10000, value));
}

function validateCrossoverDays(value) {
    value = parseInt(value) || 365;
    return Math.max(30, Math.min(1000, value));
}

// Ticker Search Functions
function searchTicker(query) {
    if (query.length < 1) {
        hideSearchResults();
        return;
    }

    fetch(`/search_ticker?query=${encodeURIComponent(query)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            displaySearchResults(data);
        })
        .catch(error => {
            console.error('Search error:', error);
            hideSearchResults();
        });
}

function displaySearchResults(data) {
    const resultsDiv = document.getElementById('search-results');
    if (!resultsDiv) return;

    if (data && data.length > 0) {
        const html = data.map(item => `
            <div class="search-item" onclick="selectTicker('${item.symbol}')">
                <span class="symbol">${item.symbol}</span>
                ${item.name ? `<span class="name">${item.name}</span>` : ''}
            </div>
        `).join('');
        
        resultsDiv.innerHTML = html;
        resultsDiv.style.display = 'block';
    } else {
        hideSearchResults();
    }
}

function selectTicker(symbol) {
    const tickerInput = document.getElementById('ticker');
    if (tickerInput) {
        tickerInput.value = symbol;
    }
    hideSearchResults();
}

function hideSearchResults() {
    const resultsDiv = document.getElementById('search-results');
    if (resultsDiv) {
        resultsDiv.style.display = 'none';
    }
}

// Click Outside Handler
function handleClickOutside(event) {
    const searchResults = document.getElementById('search-results');
    const tickerInput = document.getElementById('ticker');
    
    if (searchResults && tickerInput) {
        if (!tickerInput.contains(event.target) && !searchResults.contains(event.target)) {
            hideSearchResults();
        }
    }
}

// Utility Functions
function formatNumber(number) {
    return new Intl.NumberFormat().format(number);
}

function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Export functions for use in other files if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        validateLookbackDays,
        validateCrossoverDays,
        searchTicker,
        selectTicker
    };
}