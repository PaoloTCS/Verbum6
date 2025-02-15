/**
 * Knowledge Landscape Visualization
 * Handles the D3.js-based Voronoi tessellation visualization of document hierarchies.
 */

class VoronoiMap {
    constructor(containerId) {
        this.container = d3.select(`#${containerId}`);
        this.width = this.container.node().getBoundingClientRect().width;
        this.height = 800;  // Match CSS height
        this.padding = 60;  // Increased padding
        this.currentPath = [];
        this.currentData = null;
        
        this.svg = this.container.append('svg')
            .attr('width', this.width)
            .attr('height', this.height);
        
        this.initialize();
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
            console.error('Failed to load data:', error);
        }
    }

    generatePoints(data) {
        const children = data.children || [];
        if (children.length === 0) return [];

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
        const points = this.generatePoints(data);
        if (points.length === 0) return;

        const delaunay = d3.Delaunay.from(points, d => d.x, d => d.y);
        const voronoi = delaunay.voronoi([
            this.padding, 
            this.padding, 
            this.width - this.padding, 
            this.height - this.padding
        ]);

        // Clear previous content
        this.svg.selectAll('*').remove();

        // Draw cells
        const cells = this.svg.append('g')
            .selectAll('g')
            .data(points)
            .join('g');

        // Update cell styling
        cells.append('path')
            .attr('d', (_, i) => `M${voronoi.cellPolygon(i).join('L')}Z`)
            .attr('class', d => `cell ${d.isMe ? 'me-node' : ''}`)
            .attr('fill', (_, i) => d3.interpolateRainbow(i / points.length))
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .style('cursor', 'pointer')
            .style('opacity', d => d.isMe ? 0.9 : 0.7)  // More transparency
            .on('click', (event, d) => this.handleCellClick(d));

        // Update labels
        cells.append('text')
            .attr('class', d => `label ${d.isMe ? 'me-label' : ''}`)
            .attr('x', d => d.x)
            .attr('y', d => d.y)
            .attr('text-anchor', 'middle')
            .attr('dy', '0.35em')
            .attr('fill', 'white')
            .style('pointer-events', 'none')
            .text(d => d.name);

        this.updateBreadcrumb();
    }

    handleCellClick(d) {
        if (d.type === 'folder') {
            this.currentPath.push(d.name);
            this.renderLevel({ children: d.children });
        } else if (d.type === 'document') {
            // Pass the document to the viewer instead of just the path
            documentViewer.show({
                name: d.name,
                path: d.path,
                type: d.type
            });
        }
    }

    updateBreadcrumb() {
        const breadcrumb = d3.select('#breadcrumb');
        breadcrumb.html('');
        
        breadcrumb.append('span')
            .text('Root')
            .style('cursor', 'pointer')
            .on('click', () => this.navigateToRoot());

        this.currentPath.forEach((path, i) => {
            breadcrumb.append('span').text(' > ');
            breadcrumb.append('span')
                .text(path)
                .style('cursor', 'pointer')
                .on('click', () => this.navigateToLevel(i));
        });
    }

    navigateToRoot() {
        this.currentPath = [];
        this.renderLevel(this.currentData.hierarchy);
    }

    navigateToLevel(level) {
        this.currentPath = this.currentPath.slice(0, level + 1);
        let currentNode = this.currentData.hierarchy;
        
        for (const pathSegment of this.currentPath) {
            currentNode = currentNode.children.find(c => c.name === pathSegment);
        }
        
        this.renderLevel(currentNode);
    }
}

// Initialize the visualization
document.addEventListener('DOMContentLoaded', () => {
    const voronoiMap = new VoronoiMap('visualization');
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
    }

    setupEventListeners() {
        document.getElementById('close-doc').onclick = () => this.hide();
        this.queryButton.onclick = () => this.handleQuery();
    }

    async handleQuery() {
        const query = this.queryInput.value.trim();
        if (!query || !this.currentDocument) return;

        try {
            this.responseDiv.textContent = 'Processing query...';
            
            const response = await fetch('/api/document/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    path: this.currentDocument.path,
                    query: query
                })
            });

            const data = await response.json();
            if (data.error) {
                this.responseDiv.textContent = `Error: ${data.error}`;
            } else {
                this.responseDiv.textContent = data.response;
            }
            
        } catch (error) {
            console.error('Error processing query:', error);
            this.responseDiv.textContent = 'Error processing query';
        }
    }

    show(document) {
        this.currentDocument = document;
        this.title.textContent = document.name;
        this.panel.classList.add('visible');
        this.loadDocument(document.path);
        
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

    async loadDocument(path) {
        try {
            const response = await fetch(`/api/document/${path}`);
            if (path.toLowerCase().endsWith('.pdf')) {
                // Handle PDF documents
                const blob = await response.blob();
                const objectUrl = URL.createObjectURL(blob);
                this.viewer.innerHTML = `
                    <iframe 
                        src="${objectUrl}" 
                        width="100%" 
                        height="100%" 
                        style="border: none; min-height: 80vh;">
                    </iframe>`;
            } else {
                // Handle text documents
                const data = await response.json();
                this.viewer.innerHTML = `<pre>${data.content}</pre>`;
            }
        } catch (error) {
            console.error('Error loading document:', error);
            this.viewer.innerHTML = '<p class="error">Error loading document</p>';
        }
    }
}

// Initialize document viewer
const documentViewer = new DocumentViewer();

// Update your cell click handler
function handleCellClick(d) {
    if (d.type === 'document') {
        documentViewer.show(d);
    }
    // ... existing navigation logic ...
}