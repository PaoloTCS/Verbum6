/**
 * Knowledge Landscape Visualization
 * Handles the D3.js-based Voronoi tessellation visualization of document hierarchies.
 */

class ErrorBoundary {
    static handleError(error, component, method) {
        console.error(`Error in ${component}.${method}:`, error);
        // You could also send this to your error tracking service
    }
}

class VoronoiMap {
    constructor(containerId, documentViewer) {
        try {
            // Add error handling for container
            const container = document.getElementById(containerId);
            if (!container) {
                throw new Error(`Container #${containerId} not found`);
            }
            
            this.container = d3.select(`#${containerId}`);
            this.width = this.container.node().getBoundingClientRect().width;
            this.height = 800;  // Match CSS height
            this.padding = 60;  // Increased padding
            this.currentPath = [];
            this.currentData = null;
            
            this.svg = this.container.append('svg')
                .attr('width', this.width)
                .attr('height', this.height);
            
            // Add resize handler
            window.addEventListener('resize', this.handleResize.bind(this));
            
            // Add loading state
            this.isLoading = false;

            this.documentViewer = documentViewer;  // Add reference to document viewer
            this.handleCellClick = this.handleCellClick.bind(this);

            this.initialize();
        } catch (error) {
            ErrorBoundary.handleError(error, 'VoronoiMap', 'constructor');
            throw error;
        }
    }

    async initialize() {
        try {
            // Fetch both hierarchy and semantic distances
            const [hierarchyResponse, distancesResponse] = await Promise.all([
                fetch('/api/hierarchy'),
                fetch('/api/semantic-distances/level-0')
            ]);
            
            this.currentData = await hierarchyResponse.json();
            const distances = await distancesResponse.json();
            
            // Merge distances into hierarchy data
            this.currentData.hierarchy.distances = distances.distances;
            this.renderLevel(this.currentData.hierarchy);
        } catch (error) {
            ErrorBoundary.handleError(error, 'VoronoiMap', 'initialize');
            this.showError('Failed to initialize visualization');
        }
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'visualization-error';
        errorDiv.innerHTML = `
            <div class="error-content">
                <div class="error-icon">⚠️</div>
                <div class="error-message">${message}</div>
            </div>
        `;
        this.container.node().appendChild(errorDiv);
    }

    generatePoints(data) {
        const children = data?.children || [];
        if (!children.length) {
            console.warn('No children in data');
            return [];
        }

        if (data.distances) {
            const points = this.positionWithForceLayout(children, data.distances);
            
            // Add "Me" node at center with more space
            if (points.some(p => p.name === "Me")) {
                const meNode = points.find(p => p.name === "Me");
                meNode.x = this.width / 2;
                meNode.y = this.height / 2;
                meNode.fixed = true;  // Don't move in force simulation
                meNode.isMe = true;  // Flag for special styling
            }
            
            return points;
        }

        return this.circularLayout(children);
    }

    circularLayout(nodes) {
        const radius = Math.min(this.width, this.height) / 2.5;  // Larger radius
        return nodes.map((d, i) => ({
            ...d,
            x: this.width/2 + radius * Math.cos((i / nodes.length) * 2 * Math.PI),
            y: this.height/2 + radius * Math.sin((i / nodes.length) * 2 * Math.PI)
        }));
    }

    positionWithForceLayout(nodes, distances) {
        const simulation = d3.forceSimulation(nodes)
            .force('charge', d3.forceManyBody().strength(-2000))  // Stronger repulsion
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(100))  // Prevent overlap
            .force('semantic', this.createSemanticForce(distances))
            .stop();

        // Run the simulation
        for (let i = 0; i < 300; ++i) simulation.tick();
        
        return nodes;
    }

    createSemanticForce(distances) {
        return (alpha) => {
            Object.entries(distances).forEach(([pair, distance]) => {
                const [id1, id2] = pair.split('|');
                const node1 = this.currentData.hierarchy.children.find(n => n.name === id1);
                const node2 = this.currentData.hierarchy.children.find(n => n.name === id2);
                
                if (node1 && node2) {
                    const dx = node2.x - node1.x;
                    const dy = node2.y - node1.y;
                    const l = Math.sqrt(dx * dx + dy * dy);
                    const targetDistance = distance * 200; // Scale factor
                    
                    if (l !== 0) {
                        const force = (l - targetDistance) * alpha;
                        node1.x += dx * force / l;
                        node1.y += dy * force / l;
                        node2.x -= dx * force / l;
                        node2.y -= dy * force / l;
                    }
                }
            });
        };
    }

    renderLevel(data) {
        try {
            const points = this.generatePoints(data);
            if (!points || points.length === 0) {
                console.warn('No points to render');
                return;
            }

            // Create Voronoi generator
            const delaunay = d3.Delaunay.from(points, d => d.x, d => d.y);
            const voronoi = delaunay.voronoi([0, 0, this.width, this.height]);

            // Clear previous content
            this.svg.selectAll('*').remove();

            // Create cells group
            const cells = this.svg.selectAll('g')
                .data(points)
                .join('g')
                .attr('class', 'node');

            // Add cell paths with click handler
            cells.append('path')
                .attr('d', (_, i) => {
                    const polygon = voronoi.cellPolygon(i);
                    return polygon ? `M${polygon.join('L')}Z` : '';
                })
                .attr('class', d => `cell ${d.isMe ? 'me-node' : ''}`)
                .attr('fill', (_, i) => d3.interpolateRainbow(i / points.length))
                .on('click', (event, d) => this.handleCellClick(d));

            // Add labels
            cells.append('text')
                .attr('class', d => `label ${d.isMe ? 'me-label' : ''}`)
                .attr('x', d => d.x)
                .attr('y', d => d.y)
                .attr('dy', '0.35em')
                .text(d => d.name);

            // Update breadcrumb
            this.updateBreadcrumb();
        } catch (error) {
            ErrorBoundary.handleError(error, 'VoronoiMap', 'renderLevel');
        }
    }

    async handleCellClick(data) {
        try {
            if (!data || !data.name) {
                console.warn('Invalid cell data');
                return;
            }

            console.log('Cell clicked:', data.name);

            if (data.type === 'document') {
                try {
                    if (data.name.toLowerCase().endsWith('.pdf')) {
                        // For PDFs, open in document viewer
                        this.documentViewer.show({
                            name: data.name,
                            path: data.path,
                            type: 'pdf'
                        });
                    } else {
                        // For other documents, fetch content
                        const response = await fetch(`/api/document/${encodeURIComponent(data.path)}`);
                        if (!response.ok) throw new Error(`Failed to fetch document: ${response.statusText}`);
                        const documentData = await response.json();
                        this.documentViewer.show({
                            ...documentData,
                            path: data.path,
                            type: 'text'
                        });
                    }
                    return;
                } catch (error) {
                    console.error('Document error:', error);
                    this.showError(`Failed to load document: ${error.message}`);
                    return;
                }
            }

            // Handle directory navigation
            const newPath = [...this.currentPath, data.name];
            console.log('Navigating to:', newPath.join('/'));
            
            const response = await fetch(`/api/hierarchy/${newPath.join('/')}`);
            if (!response.ok) throw new Error(`Server returned ${response.status}`);
            
            const newData = await response.json();
            if (!newData.hierarchy) {
                throw new Error('Invalid hierarchy data received');
            }

            this.currentPath = newPath;
            this.currentData = newData;
            this.renderLevel(newData.hierarchy);

        } catch (error) {
            ErrorBoundary.handleError(error, 'VoronoiMap', 'handleCellClick');
            this.showError(`Failed to process click on ${data.name}`);
        }
    }

    updateBreadcrumb() {
        const breadcrumb = document.getElementById('breadcrumb');
        if (!breadcrumb) return;

        const pathElements = ['Root', ...this.currentPath];
        breadcrumb.innerHTML = pathElements
            .map((elem, index) => `
                <span data-index="${index}" class="breadcrumb-item">
                    ${elem}${index < pathElements.length - 1 ? ' >' : ''}
                </span>
            `)
            .join(' ');

        // Add click handlers to breadcrumb items
        breadcrumb.querySelectorAll('.breadcrumb-item').forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                this.navigateToLevel(index);
            });
        });
    }

    navigateToRoot() {
        this.currentPath = [];
        this.renderLevel(this.currentData.hierarchy);
    }

    navigateToLevel(level) {
        console.log(`Navigating to level: ${level}`);
        console.log('Current path:', this.currentPath);
        
        this.currentPath = this.currentPath.slice(0, level + 1);
        let currentNode = this.currentData.hierarchy;
        
        for (const pathSegment of this.currentPath) {
            console.log(`Looking for segment: ${pathSegment}`);
            currentNode = currentNode.children.find(c => c.name === pathSegment);
            if (!currentNode) {
                console.error(`Failed to find node for segment: ${pathSegment}`);
                return;
            }
        }
        
        console.log('Found node:', currentNode);
        this.renderLevel(currentNode);
    }

    handleResize() {
        // Debounce resize events
        clearTimeout(this.resizeTimer);
        this.resizeTimer = setTimeout(() => {
            this.width = this.container.node().getBoundingClientRect().width;
            this.renderLevel(this.currentData.hierarchy);
        }, 250);
    }
}

// Initialize the visualization
document.addEventListener('DOMContentLoaded', () => {
    const documentViewer = new DocumentViewer();
    const voronoiMap = new VoronoiMap('visualization', documentViewer);
});

class DocumentViewer {
    constructor() {
        this.panel = document.getElementById('document-panel');
        this.viewer = document.getElementById('document-viewer');
        this.title = document.getElementById('doc-title');
        this.queryContainer = document.getElementById('query-container');
        this.queryInput = document.getElementById('doc-query');
        this.queryButton = document.getElementById('query-submit');
        this.responseDiv = document.getElementById('query-response');
        this.currentDocument = null;
        
        this.setupEventListeners();
        this.marked = marked;
        this.marked.setOptions({
            gfm: true,
            breaks: true,
            highlight: function(code) {
                return hljs.highlightAuto(code).value;
            }
        });
    }

    setupEventListeners() {
        document.getElementById('close-doc').onclick = () => this.hide();
        this.queryButton.onclick = () => this.handleQuery();
    }

    async handleQuery() {
        try {
            this.showLoadingState();
            const query = this.queryInput.value.trim();
            
            const response = await fetch('/api/document/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path: this.currentDocument.path,
                    query: query
                })
            });

            const data = await response.json();
            
            if (data.error) {
                this.showError(`
### Error Processing Query

${data.error}

${data.suggestion ? `**Suggestion:** ${data.suggestion}` : ''}

*Try breaking your question into smaller, more specific parts.*
                `);
            } else {
                this.displayResponse(data);
            }
        } catch (error) {
            this.showError('Network or processing error occurred');
        } finally {
            this.hideLoadingState();
        }
    }

    displayResponse(data) {
        try {
            const container = document.createElement('div');
            container.className = 'query-response-container';

            // Add metadata header with null checks
            const metadata = document.createElement('div');
            metadata.className = 'response-metadata';
            const chaptersProcessed = data.chapters_processed || [];
            metadata.innerHTML = `
                <div class="metadata-header">
                    <span class="document-name">${data.source_document || 'Unknown document'}</span>
                    <span class="chapter-count">${chaptersProcessed.length} chapters analyzed</span>
                </div>
                <div class="chapters-list">
                    ${chaptersProcessed.length > 0 
                      ? `Chapters: ${chaptersProcessed.join(', ')}`
                      : 'No chapters processed'}
                </div>
            `;
            container.appendChild(metadata);

            // Add main response with Markdown rendering
            const response = document.createElement('div');
            response.className = 'response-content';
            response.innerHTML = this.marked.parse(data.answer || 'No response available');
            container.appendChild(response);

            this.responseDiv.innerHTML = '';
            this.responseDiv.appendChild(container);
        } catch (error) {
            ErrorBoundary.handleError(error, 'DocumentViewer', 'displayResponse');
            this.showError('Error displaying response');
        }
    }

    showLoadingState() {
        if (this.responseDiv) {
            this.responseDiv.innerHTML = `
                <div class="loading-indicator">
                    <div class="spinner"></div>
                    <div>Processing query across chapters...</div>
                </div>
            `;
        }
    }

    hideLoadingState() {
        if (this.responseDiv) {
            const loadingIndicator = this.responseDiv.querySelector('.loading-indicator');
            if (loadingIndicator) {
                loadingIndicator.remove();
            }
        }
    }

    showError(message) {
        this.responseDiv.innerHTML = `
            <div class="error-message">
                <div class="error-icon">⚠️</div>
                <div>${message}</div>
            </div>
        `;
    }

    show(document) {
        this.currentDocument = document;
        this.title.textContent = document.name;
        this.panel.classList.add('visible');
        this.loadDocument(document);
        
        // Show query interface only for PDF documents
        if (document.name.toLowerCase().endsWith('.pdf')) {
            this.queryContainer.classList.remove('hidden');
        } else {
            this.queryContainer.classList.add('hidden');
        }
    }

    hide() {
        this.panel.classList.remove('visible');
        this.viewer.innerHTML = '';
        this.responseDiv.textContent = '';
        this.queryInput.value = '';
        this.currentDocument = null;
        this.queryContainer.classList.add('hidden');
    }

    async loadDocument(document) {
        try {
            if (document.type === 'pdf') {
                // Load PDF directly in iframe
                const docPath = `/api/document/${encodeURIComponent(document.path)}`;
                this.viewer.innerHTML = `
                    <iframe 
                        src="${docPath}" 
                        width="100%" 
                        height="100%" 
                        style="border: none; min-height: 80vh;">
                    </iframe>`;
            } else {
                // Display text content
                const response = await fetch(`/api/document/${encodeURIComponent(document.path)}`);
                if (!response.ok) throw new Error('Failed to load document');
                const data = await response.json();
                this.viewer.innerHTML = `<pre>${data.content}</pre>`;
            }
        } catch (error) {
            console.error('Error loading document:', error);
            this.viewer.innerHTML = `
                <div class="error-message">
                    Failed to load document: ${error.message}
                </div>`;
        }
    }

    async submitQuery(query) {
        try {
            if (!this.currentDocument || !query.trim()) {
                this.showError('No document loaded or empty query');
                return;
            }

            this.showLoading();
            
            const response = await fetch('/api/document/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    path: this.currentDocument.path,
                    query: query.trim()
                })
            });

            const result = await response.json();

            if (!response.ok || result.error) {
                throw new Error(result.error || result.details || 'Failed to process query');
            }

            this.displayResponse(result);

        } catch (error) {
            console.error('Query error:', error);
            this.showError(`Query processing failed: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    displayResponse(data) {
        this.responseDiv.innerHTML = `
            <div class="query-response">
                <p class="answer">${data.answer}</p>
                <p class="metadata">
                    Source: ${data.source_document}<br>
                    Pages processed: ${data.pages_processed}
                </p>
            </div>
        `;
    }

    showLoading() {
        this.responseDiv.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>Processing query...</p>
            </div>
        `;
    }

    hideLoading() {
        const loadingElement = this.responseDiv.querySelector('.loading');
        if (loadingElement) {
            loadingElement.remove();
        }
    }
}