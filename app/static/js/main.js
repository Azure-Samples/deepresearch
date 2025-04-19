// TypeScript-like implementation for the Azure Deep Research frontend

// DOM Elements
const researchInput = document.getElementById('research-input');
const researchButton = document.getElementById('research-button');
const progressContainer = document.getElementById('progress-container');
const progressSteps = document.getElementById('progress-steps');
const progressStatus = document.getElementById('progress-status');
const resultsContainer = document.getElementById('results-container');
const resultsContent = document.getElementById('results-content');
const thoughtBubbleButton = document.getElementById('thought-bubble-button');
const thinkingModal = document.getElementById('thinking-modal');
const closeThinkingModalButton = document.getElementById('close-thinking-modal');
const modalThinkingContent = document.getElementById('modal-thinking-content');

// State
let websocket;
let clientId = generateId();
let currentResearchTopic = '';
let researchInProgress = false;
let stepsCompleted = new Set();
let currentStep = '';
let latestThoughts = '';  // Store the latest thoughts

// Step definitions
const researchSteps = {
    'generate_query': { 
        name: 'Generate Query', 
        description: 'Creating optimal search queries for your topic',
        icon: '🔍'
    },
    'web_research': { 
        name: 'Web Research', 
        description: 'Searching the internet for relevant information',
        icon: '🌐'
    },
    'summarize': { 
        name: 'Summarize', 
        description: 'Summarizing and analyzing findings',
        icon: '📝'
    },
    'reflection': { 
        name: 'Reflection', 
        description: 'Finding knowledge gaps for deeper research',
        icon: '💭'
    },
    'finalize': { 
        name: 'Finalize Report', 
        description: 'Compiling comprehensive research results',
        icon: '📊'
    },
    'routing': { 
        name: 'Routing', 
        description: 'Routing research for further exploration',
        icon: '⚙️'
    }
};

// Helper functions
function generateId() {
    return 'user-' + Math.random().toString(36).substring(2, 15);
}

function showElement(element) {
    element.classList.remove('hidden');
    element.classList.add('fade-in');
}

function hideElement(element) {
    element.classList.add('hidden');
}

function renderMarkdown(markdown) {
    if (!markdown) return '';
    
    // Convert headers
    markdown = markdown.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
    markdown = markdown.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    markdown = markdown.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    markdown = markdown.replace(/^#### (.*?)$/gm, '<h4>$1</h4>');
    markdown = markdown.replace(/^##### (.*?)$/gm, '<h5>$1</h5>');
    
    // Convert bold and italic
    markdown = markdown.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    markdown = markdown.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Convert links
    markdown = markdown.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" class="text-blue-600 hover:underline">$1</a>');
    
    // Convert bullet points
    markdown = markdown.replace(/^- (.*?)$/gm, '<li>$1</li>');
    markdown = markdown.replace(/^\* (.*?)$/gm, '<li>$1</li>');
    
    // Convert numbered lists
    markdown = markdown.replace(/^\d+\. (.*?)$/gm, '<li>$1</li>');
    
    // Wrap lists
    markdown = markdown.replace(/(<li>.*?<\/li>\n)+/gs, function(match) {
        if(match.includes('1. ') || match.includes('2. ')) {
            return '<ol class="list-decimal pl-6 mb-4">' + match + '</ol>';
        }
        return '<ul class="list-disc pl-6 mb-4">' + match + '</ul>';
    });
    
    // Convert code blocks
    markdown = markdown.replace(/```([^`]*?)```/gs, '<pre class="bg-gray-100 p-2 rounded my-2 overflow-x-auto text-sm font-mono">$1</pre>');
    
    // Convert inline code
    markdown = markdown.replace(/`([^`]*?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">$1</code>');
    
    // Convert blockquotes
    markdown = markdown.replace(/^> (.*?)$/gm, '<blockquote class="border-l-4 border-gray-300 pl-4 italic text-gray-700">$1</blockquote>');
    
    // Convert horizontal rules
    markdown = markdown.replace(/^---$/gm, '<hr class="my-4 border-t border-gray-300">');
    
    // Convert paragraphs (must be last)
    const paragraphs = markdown.split(/\n\n+/);
    markdown = paragraphs.map(p => {
        // Skip if already has HTML tags
        if (p.trim().startsWith('<') && !p.trim().startsWith('<li>')) {
            return p;
        }
        return '<p class="mb-4">' + p + '</p>';
    }).join('\n');
    
    return markdown;
}

function createStepElement(step, status = 'pending') {
    const stepInfo = researchSteps[step] || { 
        name: step, 
        description: 'Processing', 
        icon: '⚙️' 
    };
    
    const stepElement = document.createElement('li');
    stepElement.id = `step-${step}`;
    stepElement.classList.add('flex', 'items-start', 'gap-4');
    
    if (status === 'active') {
        stepElement.classList.add('step-active');
    } else if (status === 'complete') {
        stepElement.classList.add('step-complete');
    }
    
    stepElement.innerHTML = `
        <div class="step-icon">
            ${stepInfo.icon}
        </div>
        <div class="flex-1">
            <h3 class="font-semibold">${stepInfo.name}</h3>
            <p class="text-sm text-gray-600">${stepInfo.description}</p>
            <div id="step-${step}-details" class="mt-2 text-sm"></div>
        </div>
    `;
    
    return stepElement;
}

function updateStepDetails(step, data) {
    const stepDetailsElement = document.getElementById(`step-${step}-details`);
    if (!stepDetailsElement) return;
    
    let detailsContent = '';
    
    switch (step) {
        case 'generate_query':
            detailsContent = `<div class="text-blue-600 font-medium">"${data.query}"</div>
                             <div class="text-gray-500 text-xs mt-1">${data.rationale}</div>`;
            break;
        case 'web_research':
            detailsContent = `<div class="text-xs text-gray-500">Found ${data.sources?.length || 0} sources</div>`
                             + (data.sources ? `<ul class="list-disc pl-4 mt-1">${data.sources.map(src => `<li>${src}</li>`).join('')}</ul>` : ''); 
            break;
        case 'summarize':
            detailsContent = `<div class="text-xs text-gray-500">Building comprehensive summary...</div>`;
            break;
        case 'reflection':
            detailsContent = `<div class="text-blue-600 font-medium">"${data.query}"</div>
                             <div class="text-gray-500 text-xs mt-1">Identified gap: ${data.knowledge_gap}</div>`;
            break;
        case 'routing':
            if (data.loop_count <= 3) {
                detailsContent = `<div class="text-xs text-gray-500">Research cycle ${data.loop_count} - continuing research...</div>`;
            } else {
                detailsContent = `<div class="text-xs text-gray-500">Research cycles complete - finalizing report...</div>`;
            }
            break;
    }
    
    stepDetailsElement.innerHTML = detailsContent;
}

// WebSocket Connection
function connectWebSocket() {
    websocket = new WebSocket(`ws://${window.location.host}/ws/${clientId}`);
    
    websocket.onopen = () => {
        console.log('WebSocket connection established');
    };
    
    websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    websocket.onclose = () => {
        console.log('WebSocket connection closed');
        if (researchInProgress) {
            // Attempt reconnection if research is in progress
            setTimeout(connectWebSocket, 1000);
        }
    };
    
    websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

function handleWebSocketMessage(message) {
    const { type, data } = message;
    
    switch(type) {
        case 'generate_query':
            updateResearchProgress('generate_query', 'complete', data);
            showThinkingProcess(data.thoughts);
            break;
            
        case 'web_research':
            updateResearchProgress('web_research', 'complete', data);
            break;
            
        case 'summarize':
            updateResearchProgress('summarize', 'complete', data);
            showThinkingProcess(data.thoughts);
            break;
            
        case 'thinking':
            showThinkingProcess(data.thoughts);
            break;
            
        case 'reflection':
            updateResearchProgress('reflection', 'complete', data);
            showThinkingProcess(data.thoughts);
            break;
            
        case 'routing':
            updateResearchProgress('routing', 'complete', data);
            if (data.decision === 'continue') {
                // Reset active statuses but keep completed ones
                updateNextActiveStep('generate_query');
            }
            break;
            
        case 'finalize':
            updateResearchProgress('finalize', 'complete', data);
            replaceSpinnerWithCheckmark();
            finishResearch(data.summary || '');
            break;
    }
}

function updateResearchProgress(step, status, data) {
    // Mark the previous step as completed if this is a new step
    if (currentStep && currentStep !== step) {
        stepsCompleted.add(currentStep);
        const prevStepElement = document.getElementById(`step-${currentStep}`);
        if (prevStepElement) {
            prevStepElement.classList.remove('step-active');
            prevStepElement.classList.add('step-complete');
        }
    }
    
    // Update the current step
    currentStep = step;
    
    // Add step to UI if it doesn't exist yet
    let stepElement = document.getElementById(`step-${step}`);
    if (!stepElement) {
        stepElement = createStepElement(step, status);
        progressSteps.appendChild(stepElement);
    } else {
        // Update existing step status
        stepElement.classList.remove('step-active', 'step-complete');
        stepElement.classList.add(`step-${status}`);
    }
    
    // Update step details if data is provided
    if (data) {
        updateStepDetails(step, data);
    }
    
    // Update progress status text
    if (researchSteps[step]) {
        progressStatus.textContent = `${researchSteps[step].name} in progress...`;
    }
}

function updateNextActiveStep(nextStep) {
    updateResearchProgress(nextStep, 'active');
}

function showThinkingProcess(thoughts) {
    // Remove XML tags from thoughts
    const cleanedThoughts = thoughts.replace(/<\/?think>/g, '');
    
    if (cleanedThoughts.trim()) {
        latestThoughts = cleanedThoughts; // Store the latest thoughts
    }
}

function replaceSpinnerWithCheckmark() {
    // Replace the spinner with a checkmark
    const spinner = document.querySelector('.loading-spinner');
    if (spinner) {
        // Create a checkmark element to replace the spinner
        const checkmark = document.createElement('div');
        checkmark.className = 'checkmark';
        spinner.parentNode.replaceChild(checkmark, spinner);
    }
}

function finishResearch(summary) {
    researchInProgress = false;
    progressStatus.textContent = 'Research completed!';
    
    // Replace the spinner with a checkmark
    const spinner = document.querySelector('.loading-spinner');
    if (spinner) {
        // Create a checkmark element to replace the spinner
        const checkmark = document.createElement('div');
        checkmark.className = 'checkmark';
        spinner.parentNode.replaceChild(checkmark, spinner);
    }
    
    // Display the results
    showElement(resultsContainer);
    resultsContent.innerHTML = renderMarkdown(summary);
    
    // Enable the research button again
    researchButton.disabled = false;
    researchButton.textContent = 'Research';
    researchButton.classList.remove('opacity-50');
}

function startResearch() {
    const topic = researchInput.value.trim();
    if (!topic) return;
    
    currentResearchTopic = topic;
    researchInProgress = true;
    
    // Reset state
    stepsCompleted.clear();
    currentStep = '';
    
    // Clear previous results
    progressSteps.innerHTML = '';
    resultsContent.innerHTML = '';
    
    // Show progress tracking and hide any previous results
    showElement(progressContainer);
    hideElement(resultsContainer);
    
    // Reset progress status display
    progressStatus.textContent = 'Initializing...';
    
    // Replace any checkmark with spinner
    const checkmark = document.querySelector('.checkmark');
    if (checkmark) {
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        checkmark.parentNode.replaceChild(spinner, checkmark);
    } else {
        // Make sure there's a spinner next to the status
        const progressStatusContainer = progressStatus.parentNode;
        if (!progressStatusContainer.querySelector('.loading-spinner')) {
            const spinner = document.createElement('div');
            spinner.className = 'loading-spinner';
            progressStatusContainer.appendChild(spinner);
        }
    }
    
    // Disable button during research
    researchButton.disabled = true;
    researchButton.textContent = 'Researching...';
    researchButton.classList.add('opacity-50');
    
    // Set initial step
    updateNextActiveStep('generate_query');
    
    // Send research request to server
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({
            type: 'research',
            topic: topic
        }));
    } else {
        progressStatus.textContent = 'Connection error. Trying to reconnect...';
        connectWebSocket();
        setTimeout(() => {
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({
                    type: 'research',
                    topic: topic
                }));
            } else {
                progressStatus.textContent = 'Unable to connect. Please refresh the page.';
                researchButton.disabled = false;
                researchButton.textContent = 'Research';
                researchButton.classList.remove('opacity-50');
            }
        }, 1000);
    }
}

// Event Listeners
window.addEventListener('DOMContentLoaded', () => {
    // Connect to WebSocket
    connectWebSocket();
    
    // Add event listener to research button
    researchButton.addEventListener('click', startResearch);
    
    // Add event listener for Enter key in input field
    researchInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            startResearch();
        }
    });

    // Add event listener to thought bubble button
    thoughtBubbleButton.addEventListener('click', () => {
        modalThinkingContent.textContent = latestThoughts;
        showElement(thinkingModal);
    });

    // Add event listener to close modal button
    closeThinkingModalButton.addEventListener('click', () => {
        hideElement(thinkingModal);
    });
});
