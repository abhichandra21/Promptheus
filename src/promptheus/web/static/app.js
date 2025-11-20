// Promptheus Web UI - Modern Application Controller
class PromptheusApp {
    constructor() {
        this.apiBaseUrl = window.location.origin;
        this.currentHistoryPage = 0; // 0-based page index
        this.currentPageSize = 20;
        this.totalHistoryPages = 0;
        this.currentAbortController = null;
        this.currentEventSource = null;
        this.streamingText = '';
        this.streamingInterval = null;
        this.currentOptimizedPrompt = ''; // Store current prompt
        this.cachedModels = {}; // Store fetched models by provider ID
        this.hasResults = false; // Track if we have results displayed
        this.init();
    }

    init() {
        // Configure marked.js to reduce extra spacing
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                breaks: false,  // Don't convert \n to <br>
                gfm: true,      // GitHub Flavored Markdown
                headerIds: false,
                mangle: false
            });
        }
        this.bindEvents();
        this.loadProviders();
        this.loadHistory();
        this.loadSettings();
    }

    bindEvents() {
        // Main prompt submission
        document.getElementById('submit-btn').addEventListener('click', () => this.submitPrompt());

        // Keyboard shortcuts
        document.getElementById('prompt-input').addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.submitPrompt();
            }
        });

        // New prompt button (hidden initially, shown after results)
        document.getElementById('start-over-btn').addEventListener('click', () => {
            this.startNewPrompt();
        });

        // Track input changes to detect new prompts (but only when we have results)
        const promptInput = document.getElementById('prompt-input');
        let lastPromptValue = '';
        promptInput.addEventListener('input', () => {
            if (this.hasResults) {
                this.handleInputChange(promptInput.value, lastPromptValue);
                lastPromptValue = promptInput.value;
            }
        });

        // Provider selection
        document.getElementById('provider-select').addEventListener('change', (e) => {
            this.selectProvider(e.target.value);
            this.loadModelsForProvider(e.target.value);
        });

        // Model selection
        document.getElementById('model-select').addEventListener('change', (e) => {
            this.selectModel(e.target.value);
        });

        // Copy button
        document.getElementById('copy-btn').addEventListener('click', () => {
            this.copyOutputToClipboard();
        });

        // Tweak button
        document.getElementById('tweak-btn').addEventListener('click', () => {
            this.showTweakPromptDialog();
        });

        // Settings panel controls
        document.getElementById('settings-btn').addEventListener('click', () => {
            this.openSettings();
        });

        document.getElementById('settings-close-btn').addEventListener('click', () => {
            this.closeSettings();
        });

        document.getElementById('settings-overlay').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                this.closeSettings();
            }
        });

        // Escape key to close settings
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeSettings();
            }
        });

        // History pagination
        document.getElementById('prev-page-btn').addEventListener('click', () => {
            this.previousHistoryPage();
        });

        document.getElementById('next-page-btn').addEventListener('click', () => {
            this.nextHistoryPage();
        });

        document.getElementById('page-size-select').addEventListener('change', (e) => {
            this.currentPageSize = parseInt(e.target.value);
            this.currentHistoryPage = 0;
            this.loadHistory();
        });

        // Cancel button
        document.getElementById('cancel-btn').addEventListener('click', () => {
            this.cancelCurrentRequest();
        });

        // Clear history button
        document.getElementById('clear-history-btn').addEventListener('click', () => {
            this.clearHistory();
        });
    }

    /* ===================================================================
       SETTINGS PANEL MANAGEMENT
       =================================================================== */

    openSettings() {
        const overlay = document.getElementById('settings-overlay');
        const panel = document.getElementById('settings-panel');

        overlay.classList.add('active');
        panel.classList.add('active');

        // Focus first focusable element
        setTimeout(() => {
            const firstInput = panel.querySelector('input, button, select');
            if (firstInput) firstInput.focus();
        }, 300);
    }

    closeSettings() {
        const overlay = document.getElementById('settings-overlay');
        const panel = document.getElementById('settings-panel');

        overlay.classList.remove('active');
        panel.classList.remove('active');
    }

    /* ===================================================================
       INPUT STATE MANAGEMENT
       =================================================================== */

    startNewPrompt() {
        const promptInput = document.getElementById('prompt-input');
        const outputDiv = document.getElementById('output');
        const tweakBtn = document.getElementById('tweak-btn');
        const copyBtn = document.getElementById('copy-btn');
        const startOverBtn = document.getElementById('start-over-btn');

        // Clear the input field and reset state
        promptInput.value = '';
        this.hasResults = false;

        // Clear output with transition
        this.clearOutputWithTransition();

        // Hide action buttons and start over button
        tweakBtn.classList.add('hidden');
        copyBtn.classList.add('hidden');
        startOverBtn.classList.add('hidden');

        // Update placeholder text to initial state
        promptInput.placeholder = 'Enter your prompt here...';

        // Focus input for convenience
        promptInput.focus();
    }

    showResultsState() {
        const promptInput = document.getElementById('prompt-input');
        const startOverBtn = document.getElementById('start-over-btn');

        this.hasResults = true;

        // Update placeholder to indicate they can optimize another prompt
        promptInput.placeholder = 'Optimize another prompt...';

        // Show the "Start Over" button
        startOverBtn.classList.remove('hidden');
    }

    handleInputChange(currentValue, lastValue) {
        const outputDiv = document.getElementById('output');
        const hasOutput = outputDiv.querySelector('.optimized-prompt-content');

        if (!hasOutput) return;

        // Calculate similarity between current and last prompt
        const isSimilar = this.calculateSimilarity(currentValue, lastValue) > 0.7;

        // If user is typing something significantly different (more than 10 chars changed)
        if (!isSimilar && currentValue.length > 10 && Math.abs(currentValue.length - lastValue.length) > 5) {
            this.clearOutputWithTransition();
            this.hasResults = false;
            document.getElementById('start-over-btn').classList.add('hidden');
            document.getElementById('tweak-btn').classList.add('hidden');
            document.getElementById('copy-btn').classList.add('hidden');
        }
    }

    calculateSimilarity(str1, str2) {
        if (!str1 || !str2) return 0;

        const longer = str1.length > str2.length ? str1 : str2;
        const shorter = str1.length > str2.length ? str2 : str1;

        if (longer.length === 0) return 1.0;

        const editDistance = this.levenshteinDistance(longer, shorter);
        return (longer.length - editDistance) / longer.length;
    }

    levenshteinDistance(str1, str2) {
        const matrix = [];

        for (let i = 0; i <= str2.length; i++) {
            matrix[i] = [i];
        }

        for (let j = 0; j <= str1.length; j++) {
            matrix[0][j] = j;
        }

        for (let i = 1; i <= str2.length; i++) {
            for (let j = 1; j <= str1.length; j++) {
                if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
                    matrix[i][j] = matrix[i - 1][j - 1];
                } else {
                    matrix[i][j] = Math.min(
                        matrix[i - 1][j - 1] + 1,
                        matrix[i][j - 1] + 1,
                        matrix[i - 1][j] + 1
                    );
                }
            }
        }

        return matrix[str2.length][str1.length];
    }

    clearOutputWithTransition() {
        const outputDiv = document.getElementById('output');
        const tweakBtn = document.getElementById('tweak-btn');
        const copyBtn = document.getElementById('copy-btn');

        // Add fade-out class
        outputDiv.style.opacity = '0';
        outputDiv.style.transition = 'opacity 0.2s ease-out';

        setTimeout(() => {
            // Clear output and show ready state
            outputDiv.innerHTML = `
                <p class="message message-info">
                    <span>💡</span>
                    <span>Your optimized prompt will appear here</span>
                </p>
            `;

            // Hide tweak and copy buttons
            tweakBtn.classList.add('hidden');
            copyBtn.classList.add('hidden');

            // Fade back in
            setTimeout(() => {
                outputDiv.style.opacity = '1';
                outputDiv.style.transition = 'opacity 0.3s ease-in';
            }, 50);
        }, 200);
    }

    /* ===================================================================
       PROMPT SUBMISSION & PROCESSING
       =================================================================== */

    async submitPrompt() {
        const promptInput = document.getElementById('prompt-input');
        const outputDiv = document.getElementById('output');
        const submitBtn = document.getElementById('submit-btn');
        const cancelBtn = document.getElementById('cancel-btn');
        const questionMode = document.getElementById('question-mode').value;

        const prompt = promptInput.value.trim();
        if (!prompt) {
            this.showMessage('error', 'Please enter a prompt');
            return;
        }

        const provider = document.getElementById('provider-select').value;
        let model = document.getElementById('model-select')?.value || null;

        // Don't send the "load all models" placeholder as an actual model
        if (model === '__load_all__') {
            model = null; // Let backend use auto/default model
        }

        // Determine skip_questions and force_questions from mode
        const skipQuestions = questionMode === 'skip';
        const forceQuestions = questionMode === 'force';

        // Cancel any existing request
        if (this.currentAbortController) {
            this.currentAbortController.abort();
        }

        // Create new AbortController
        this.currentAbortController = new AbortController();

        // Show loading state - keep button visible at top
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span><span>Processing...</span>';
        cancelBtn.classList.remove('hidden');

        try {
            // Check if clarifying questions are needed
            if (!skipQuestions) {
                // Show analyzing indicator while generating questions
                this.showProgressIndicator('analyzing');

                const questionsResponse = await fetch(`${this.apiBaseUrl}/api/questions/generate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prompt,
                        provider: provider || null,
                        force_questions: forceQuestions
                    }),
                    signal: this.currentAbortController.signal
                });

                if (this.currentAbortController.signal.aborted) return;

                const questionsData = await questionsResponse.json();

                if (this.currentAbortController.signal.aborted) return;

                if (questionsData.success && questionsData.questions && questionsData.questions.length > 0) {
                    const answersResult = await this.showQuestionsAndCollectAnswers(questionsData.questions);

                    if (answersResult === null) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = '<span>Optimize Prompt</span>';
                        cancelBtn.classList.add('hidden');
                        return;
                    }

                    const { responses, mapping } = answersResult;

                    // Show refining indicator
                    this.showProgressIndicator('refining');

                    // Submit with answers
                    const response = await fetch(`${this.apiBaseUrl}/api/prompt/submit`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            prompt,
                            provider: provider || null,
                            model: model || null,
                            skip_questions: false,
                            refine: forceQuestions,
                            answers: responses,
                            question_mapping: mapping
                        }),
                        signal: this.currentAbortController.signal
                    });

                    if (this.currentAbortController.signal.aborted) return;

                    const data = await response.json();
                    this.handlePromptResponse(data);
                } else {
                    await this.submitPromptDirect(prompt, provider, skipQuestions, forceQuestions);
                }
            } else {
                await this.submitPromptDirect(prompt, provider, skipQuestions, forceQuestions);
            }
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('Error submitting prompt:', error);
            this.showMessage('error', 'Network error: ' + error.message);
        } finally {
            this.currentAbortController = null;
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span>Optimize Prompt</span>';
            cancelBtn.classList.add('hidden');
        }
    }

    async submitPromptDirect(prompt, provider, skipQuestions, forceQuestions = false) {
        const outputDiv = document.getElementById('output');
        const tweakBtn = document.getElementById('tweak-btn');
        const copyBtn = document.getElementById('copy-btn');
        let model = document.getElementById('model-select')?.value || null;

        // Don't send the "load all models" placeholder as an actual model
        if (model === '__load_all__') {
            model = null; // Let backend use auto/default model
        }

        // Use streaming endpoint
        const params = new URLSearchParams({
            prompt,
            skip_questions: skipQuestions,
            refine: forceQuestions
        });

        if (provider) params.append('provider', provider);
        if (model) params.append('model', model);

        // Show optimizing indicator briefly before streaming
        this.showProgressIndicator(forceQuestions ? 'refining' : 'optimizing');

        // Small delay to let the progress indicator display
        await new Promise(resolve => setTimeout(resolve, 200));

        this.streamingText = '';
        outputDiv.innerHTML = '<div class="optimized-prompt-content streaming"><span class="streaming-cursor">|</span></div>';

        const eventSource = new EventSource(`${this.apiBaseUrl}/api/prompt/stream?${params.toString()}`);
        this.currentEventSource = eventSource;

        const contentDiv = outputDiv.querySelector('.optimized-prompt-content');
        const cursorSpan = contentDiv.querySelector('.streaming-cursor');

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'token') {
                this.streamingText += data.content;
                contentDiv.textContent = this.streamingText;
                contentDiv.appendChild(cursorSpan);
            } else if (data.type === 'done') {
                eventSource.close();
                this.currentEventSource = null;
                cursorSpan.remove();
                contentDiv.classList.remove('streaming');
                this.currentOptimizedPrompt = this.streamingText; // Store for markdown toggle
                tweakBtn.classList.remove('hidden'); // Show tweak button
                copyBtn.classList.remove('hidden'); // Show copy button
                this.showResultsState(); // Show contextual results state
                this.loadHistory();
            } else if (data.type === 'error') {
                eventSource.close();
                this.currentEventSource = null;
                tweakBtn.classList.add('hidden');
                copyBtn.classList.add('hidden');
                this.showMessage('error', data.content);
            }
        };

        eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            eventSource.close();
            this.currentEventSource = null;

            if (!this.streamingText) {
                this.showMessage('error', 'Streaming connection failed');
            } else {
                cursorSpan.remove();
                contentDiv.classList.remove('streaming');
            }
        };
    }

    handlePromptResponse(data) {
        const outputDiv = document.getElementById('output');
        const tweakBtn = document.getElementById('tweak-btn');
        const copyBtn = document.getElementById('copy-btn');

        if (data.success) {
            this.currentOptimizedPrompt = data.refined_prompt;
            this.renderOutput();
            tweakBtn.classList.remove('hidden'); // Show tweak button
            copyBtn.classList.remove('hidden'); // Show copy button
            this.showResultsState(); // Show contextual results state
            this.loadHistory();
        } else {
            this.showMessage('error', data.error || 'Failed to process prompt');
            tweakBtn.classList.add('hidden');
            copyBtn.classList.add('hidden');
        }
    }

    renderOutput() {
        const outputDiv = document.getElementById('output');

        // Remove redundant "Optimized Prompt" heading if present
        let cleanedPrompt = this.currentOptimizedPrompt.trim();

        // Remove common redundant headings
        const redundantHeadings = [
            /^#\s*Optimized Prompt\s*\n+/i,
            /^##\s*Optimized Prompt\s*\n+/i,
            /^\*\*Optimized Prompt\*\*\s*\n+/i,
            /^Optimized Prompt:\s*\n+/i
        ];

        for (const pattern of redundantHeadings) {
            cleanedPrompt = cleanedPrompt.replace(pattern, '');
        }

        // Enhanced plain text rendering with selective formatting
        const formattedText = this.formatEnhancedText(cleanedPrompt);
        outputDiv.innerHTML = `<div class="optimized-prompt-content">${formattedText}</div>`;
    }

    formatEnhancedText(text) {
        // Escape HTML first
        let formatted = this.escapeHtml(text);

        // Convert **bold** to <strong>
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

        // Convert *italic* to <em>
        formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');

        // Convert `inline code` to <code>
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Preserve line breaks
        formatted = formatted.replace(/\n/g, '<br>');

        return formatted;
    }

    async showQuestionsAndCollectAnswers(questions) {
        const outputDiv = document.getElementById('output');
        const submitBtn = document.getElementById('submit-btn');

        let currentQuestionIndex = 0;
        const answers = {};
        const questionMapping = {};

        const renderQuestion = (index) => {
            const question = questions[index];
            const questionKey = `q${index}`;
            const questionText = question.question || `Question ${index + 1}`;
            const questionType = question.type || 'text';
            const required = question.required !== false;
            const isLastQuestion = index === questions.length - 1;

            questionMapping[questionKey] = questionText;

            let formHtml = '<div class="question-wizard">';

            // Progress dots
            formHtml += '<div class="wizard-progress">';
            for (let i = 0; i < questions.length; i++) {
                formHtml += `<span class="progress-dot ${i === index ? 'active' : ''} ${i < index ? 'completed' : ''}"></span>`;
            }
            formHtml += '</div>';

            // Question content
            formHtml += '<div class="wizard-content">';
            formHtml += `<div class="wizard-question-number">Question ${index + 1} of ${questions.length}</div>`;
            formHtml += `<h3 class="wizard-question-text">${this.escapeHtml(questionText)}${required ? ' <span style="color: var(--color-primary);">*</span>' : ''}</h3>`;

            formHtml += '<form id="wizard-form">';
            formHtml += '<div class="wizard-input-container">';

            if (questionType === 'radio' && question.options && question.options.length > 0) {
                question.options.forEach((option, optIndex) => {
                    formHtml += `<label class="wizard-option">`;
                    formHtml += `<input type="radio" name="${questionKey}" value="${this.escapeHtml(option)}" ${optIndex === 0 ? 'checked' : ''}>`;
                    formHtml += `<span class="wizard-option-text">${this.escapeHtml(option)}</span>`;
                    formHtml += `</label>`;
                });
            } else if (questionType === 'checkbox' && question.options && question.options.length > 0) {
                question.options.forEach((option, optIndex) => {
                    formHtml += `<label class="wizard-option">`;
                    formHtml += `<input type="checkbox" name="${questionKey}" value="${this.escapeHtml(option)}">`;
                    formHtml += `<span class="wizard-option-text">${this.escapeHtml(option)}</span>`;
                    formHtml += `</label>`;
                });
            } else {
                const savedAnswer = answers[questionKey] || '';
                const placeholder = required ? "Type your answer here..." : "Optional - Leave blank to skip";
                formHtml += `<textarea id="${questionKey}" name="${questionKey}" ${required ? 'required' : ''} class="wizard-input" placeholder="${placeholder}" rows="4">${this.escapeHtml(savedAnswer)}</textarea>`;
            }

            formHtml += '</div>'; // wizard-input-container

            // Navigation buttons
            formHtml += '<div class="wizard-actions">';

            if (index > 0) {
                formHtml += '<button type="button" id="wizard-prev-btn" class="btn btn-secondary">';
                formHtml += '<span>← Previous</span>';
                formHtml += '</button>';
            } else {
                formHtml += '<div></div>'; // Spacer
            }

            if (!required) {
                formHtml += '<button type="button" id="wizard-skip-btn" class="btn btn-tertiary">';
                formHtml += '<span>Skip</span>';
                formHtml += '</button>';
            }

            if (isLastQuestion) {
                formHtml += '<button type="submit" class="btn btn-primary">';
                formHtml += '<span>Submit Answers</span>';
                formHtml += '</button>';
            } else {
                formHtml += '<button type="submit" class="btn btn-primary">';
                formHtml += '<span>Next →</span>';
                formHtml += '</button>';
            }

            formHtml += '</div>'; // wizard-actions
            formHtml += '</form>';
            formHtml += '</div>'; // wizard-content

            // Cancel button
            formHtml += '<button type="button" id="wizard-cancel-btn" class="wizard-cancel-btn" title="Cancel">✕</button>';

            formHtml += '</div>'; // question-wizard

            outputDiv.innerHTML = formHtml;

            // Focus the input
            const firstInput = outputDiv.querySelector('input, textarea');
            if (firstInput && firstInput.type !== 'radio' && firstInput.type !== 'checkbox') {
                setTimeout(() => firstInput.focus(), 100);
            }
        };

        return new Promise((resolve) => {
            const handleNext = (form) => {
                const question = questions[currentQuestionIndex];
                const questionKey = `q${currentQuestionIndex}`;
                const questionType = question.type || 'text';

                // Collect answer
                if (questionType === 'checkbox') {
                    const checkboxes = form.querySelectorAll(`input[name="${questionKey}"]:checked`);
                    answers[questionKey] = Array.from(checkboxes).map(cb => cb.value);
                } else if (questionType === 'radio') {
                    const radio = form.querySelector(`input[name="${questionKey}"]:checked`);
                    answers[questionKey] = radio ? radio.value : '';
                } else {
                    const input = form.querySelector(`[name="${questionKey}"]`);
                    answers[questionKey] = input ? input.value : '';
                }

                // Move to next question or finish
                if (currentQuestionIndex < questions.length - 1) {
                    currentQuestionIndex++;
                    renderQuestion(currentQuestionIndex);
                    attachEventListeners();
                } else {
                    // All questions answered
                    submitBtn.innerHTML = '<span class="spinner"></span><span>Generating optimized prompt...</span>';
                    outputDiv.innerHTML = '<p class="message message-info"><span>✨</span><span>Creating your optimized prompt...</span></p>';
                    resolve({ responses: answers, mapping: questionMapping });
                }
            };

            const handlePrevious = () => {
                if (currentQuestionIndex > 0) {
                    currentQuestionIndex--;
                    renderQuestion(currentQuestionIndex);
                    attachEventListeners();
                }
            };

            const handleSkip = () => {
                const questionKey = `q${currentQuestionIndex}`;
                answers[questionKey] = '';

                if (currentQuestionIndex < questions.length - 1) {
                    currentQuestionIndex++;
                    renderQuestion(currentQuestionIndex);
                    attachEventListeners();
                } else {
                    submitBtn.innerHTML = '<span class="spinner"></span><span>Generating optimized prompt...</span>';
                    outputDiv.innerHTML = '<p class="message message-info"><span>✨</span><span>Creating your optimized prompt...</span></p>';
                    resolve({ responses: answers, mapping: questionMapping });
                }
            };

            const handleCancel = () => {
                this.cancelCurrentRequest();
                resolve(null);
            };

            const attachEventListeners = () => {
                const form = document.getElementById('wizard-form');
                const prevBtn = document.getElementById('wizard-prev-btn');
                const skipBtn = document.getElementById('wizard-skip-btn');
                const cancelBtn = document.getElementById('wizard-cancel-btn');

                if (form) {
                    form.addEventListener('submit', (e) => {
                        e.preventDefault();
                        handleNext(form);
                    });
                }

                if (prevBtn) {
                    prevBtn.addEventListener('click', handlePrevious);
                }

                if (skipBtn) {
                    skipBtn.addEventListener('click', handleSkip);
                }

                if (cancelBtn) {
                    cancelBtn.addEventListener('click', handleCancel);
                }

                // Enter key to submit
                const textInput = form?.querySelector('textarea');
                if (textInput) {
                    textInput.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter' && e.ctrlKey) {
                            e.preventDefault();
                            form.dispatchEvent(new Event('submit'));
                        }
                    });
                }
            };

            // Render first question
            renderQuestion(currentQuestionIndex);
            attachEventListeners();
        });
    }

    cancelCurrentRequest() {
        if (this.currentAbortController) {
            this.currentAbortController.abort();
            this.currentAbortController = null;
        }

        if (this.currentEventSource) {
            this.currentEventSource.close();
            this.currentEventSource = null;
        }

        const submitBtn = document.getElementById('submit-btn');
        const cancelBtn = document.getElementById('cancel-btn');
        const outputDiv = document.getElementById('output');

        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span>Optimize Prompt</span>';
        }
        if (cancelBtn) {
            cancelBtn.classList.add('hidden');
        }
        if (outputDiv) {
            this.showMessage('info', 'Request cancelled');
        }
    }

    /* ===================================================================
       PROVIDERS MANAGEMENT
       =================================================================== */

    async loadProviders() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/providers`);
            const data = await response.json();

            // Update provider select dropdown
            const providerSelect = document.getElementById('provider-select');
            providerSelect.innerHTML = '<option value="">Auto</option>';

            data.available_providers.forEach(provider => {
                const option = document.createElement('option');
                option.value = provider.id;
                option.textContent = provider.name;
                option.selected = provider.id === data.current_provider;
                providerSelect.appendChild(option);
            });

            // Load models for current provider
            if (data.current_provider) {
                await this.loadModelsForProvider(data.current_provider);
            }
        } catch (error) {
            console.error('Error loading providers:', error);
            this.showMessage('error', 'Failed to load providers');
        }
    }

    async selectProvider(providerId) {
        try {
            const payloadId = providerId || "";

            if (!providerId) {
                const modelSelect = document.getElementById('model-select');
                if (modelSelect) {
                    modelSelect.innerHTML = '<option value="">Auto</option>';
                    modelSelect.disabled = true;
                }
            }

            const response = await fetch(`${this.apiBaseUrl}/api/providers/select`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider_id: payloadId })
            });

            const data = await response.json();

            if (response.ok) {
                if (payloadId === "") {
                    this.showToast('success', 'Provider reset to auto-detect');
                } else {
                    this.showToast('success', `Provider changed to ${data.current_provider}`);
                }
            } else {
                this.showToast('error', data.detail || 'Failed to change provider');
            }
        } catch (error) {
            console.error('Error selecting provider:', error);
            this.showToast('error', 'Network error: ' + error.message);
        }
    }

    async loadModelsForProvider(providerId, fetchAll = false) {
        if (!providerId) {
            const modelSelect = document.getElementById('model-select');
            if (modelSelect) {
                modelSelect.innerHTML = '<option value="">Auto</option>';
                modelSelect.disabled = true;
            }
            return;
        }

        const modelSelect = document.getElementById('model-select');
        if (!modelSelect) return;

        try {
            // Check if we have cached models for this provider
            if (this.cachedModels[providerId] && !fetchAll) {
                const cachedData = this.cachedModels[providerId];
                this.populateModelSelect(modelSelect, cachedData.models, cachedData.current_model, false);
                return;
            }

            // Show loading state if fetching all models
            if (fetchAll) {
                modelSelect.disabled = true;
                modelSelect.innerHTML = '<option>Loading all models...</option>';
            }

            const url = fetchAll
                ? `${this.apiBaseUrl}/api/providers/${providerId}/models?fetch_all=true`
                : `${this.apiBaseUrl}/api/providers/${providerId}/models`;

            const response = await fetch(url);
            const data = await response.json();

            // Cache the models for this provider
            if (fetchAll && data.models && data.models.length > 0) {
                this.cachedModels[providerId] = {
                    models: data.models,
                    current_model: data.current_model,
                    fetchedAll: true
                };
            }

            modelSelect.innerHTML = '';
            modelSelect.disabled = false;

            this.populateModelSelect(modelSelect, data.models, data.current_model, fetchAll);

            // Show toast notification if we loaded all models
            if (fetchAll && data.models && data.models.length > 0) {
                this.showToast('success', `Loaded ${data.models.length} models for ${providerId}`);
            }
        } catch (error) {
            console.error('Error loading models:', error);
            modelSelect.innerHTML = '<option value="">Error loading models</option>';
            modelSelect.disabled = false;
            this.showToast('error', 'Failed to load models');
        }
    }

    populateModelSelect(modelSelect, models, currentModel, fetchedAll) {
        modelSelect.innerHTML = '';

        // If we got models, populate them
        if (models && models.length > 0) {
            models.forEach((model, index) => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;

                // Select current model if set, otherwise select first model
                if (currentModel) {
                    option.selected = model === currentModel;
                } else if (index === 0) {
                    option.selected = true;
                }

                modelSelect.appendChild(option);
            });
        } else {
            // No models found
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = 'No models available';
            modelSelect.appendChild(emptyOption);
        }

        // Append the "Load All Models" option last so real models stay primary
        if (!fetchedAll && models && models.length > 0) {
            const loadAllOption = document.createElement('option');
            loadAllOption.value = '__load_all__';
            loadAllOption.textContent = '↻ Load All Models...';
            loadAllOption.style.fontStyle = 'italic';
            loadAllOption.style.color = 'var(--text-secondary)';
            modelSelect.appendChild(loadAllOption);
        }
    }

    async selectModel(model) {
        const providerId = document.getElementById('provider-select').value;

        if (!providerId || !model) return;

        // Check if user selected "Load All Models"
        if (model === '__load_all__') {
            await this.loadModelsForProvider(providerId, true);
            return;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/providers/select-model`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider_id: providerId,
                    model: model
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.showToast('success', `Model changed to ${data.current_model}`);
            } else {
                this.showToast('error', data.detail || 'Failed to change model');
            }
        } catch (error) {
            console.error('Error selecting model:', error);
            this.showToast('error', 'Network error: ' + error.message);
        }
    }

    /* ===================================================================
       HISTORY MANAGEMENT
       =================================================================== */

    async loadHistory() {
        try {
            const offset = this.currentHistoryPage * this.currentPageSize;
            const response = await fetch(`${this.apiBaseUrl}/api/history?limit=${this.currentPageSize}&offset=${offset}`);
            const data = await response.json();

            const historyList = document.getElementById('history-list');
            historyList.innerHTML = '';

            if (data.entries.length === 0) {
                historyList.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📜</div>
                        <div class="empty-state-title">No History Yet</div>
                        <div class="empty-state-description">Your optimized prompts will appear here</div>
                    </div>
                `;
                this.totalHistoryPages = 0;
                this.updateHistoryPagination();
                return;
            }

            this.totalHistoryPages = Math.ceil(data.total / this.currentPageSize);

            data.entries.forEach(entry => {
                const card = this.createHistoryCard(entry);
                historyList.appendChild(card);
            });

            this.updateHistoryPagination();
        } catch (error) {
            console.error('Error loading history:', error);
            this.showMessage('error', 'Failed to load history');
        }
    }

    createHistoryCard(entry) {
        const card = document.createElement('div');
        card.className = 'history-card';
        card.setAttribute('role', 'listitem');

        const timestamp = new Date(entry.timestamp).toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        const taskType = entry.task_type || 'general';
        const badgeClass = `badge-${taskType.toLowerCase()}`;

        card.innerHTML = `
            <div class="history-card-header">
                <div class="history-card-timestamp">${timestamp}</div>
                <span class="history-card-badge ${badgeClass}">${this.escapeHtml(taskType)}</span>
            </div>
            <div class="history-card-content">
                <div class="history-card-preview">${this.escapeHtml(entry.original_prompt)}</div>
            </div>
            <div class="history-card-footer">
                <div class="history-card-meta">${this.escapeHtml(entry.provider)} • ${this.escapeHtml(entry.model)}</div>
                <button class="history-card-delete" title="Delete this entry" data-timestamp="${entry.timestamp}">
                    🗑
                </button>
            </div>
        `;

        // Add delete button handler
        const deleteBtn = card.querySelector('.history-card-delete');
        deleteBtn.addEventListener('click', async (e) => {
            e.stopPropagation(); // Prevent card click event
            await this.deleteHistoryEntry(entry.timestamp);
        });

        card.addEventListener('click', () => {
            // Restore both input and output
            const promptInput = document.getElementById('prompt-input');
            const outputDiv = document.getElementById('output');
            const tweakBtn = document.getElementById('tweak-btn');
            const copyBtn = document.getElementById('copy-btn');

            // Set the input value
            promptInput.value = entry.original_prompt;

            // Restore the optimized output if available
            if (entry.refined_prompt) {
                this.currentOptimizedPrompt = entry.refined_prompt;
                this.renderOutput();
                tweakBtn.classList.remove('hidden');
                copyBtn.classList.remove('hidden');
                this.showResultsState(); // Show contextual results state
            }

            // Scroll to top to see the restored content
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });

        return card;
    }

    previousHistoryPage() {
        if (this.currentHistoryPage > 0) {
            this.currentHistoryPage--;
            this.loadHistory();
        }
    }

    nextHistoryPage() {
        if (this.currentHistoryPage < this.totalHistoryPages - 1) {
            this.currentHistoryPage++;
            this.loadHistory();
        }
    }

    updateHistoryPagination() {
        const prevBtn = document.getElementById('prev-page-btn');
        const nextBtn = document.getElementById('next-page-btn');
        const currentPageSpan = document.getElementById('current-page');

        prevBtn.disabled = this.currentHistoryPage <= 0;
        nextBtn.disabled = this.currentHistoryPage >= this.totalHistoryPages - 1 || this.totalHistoryPages <= 1;

        const currentPageDisplay = this.currentHistoryPage + 1;
        const totalPagesDisplay = this.totalHistoryPages || 1;
        currentPageSpan.textContent = `${currentPageDisplay} of ${totalPagesDisplay}`;
    }

    async deleteHistoryEntry(timestamp) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/history/${encodeURIComponent(timestamp)}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showToast('success', 'History entry deleted');
                this.loadHistory(); // Reload to refresh the list
            } else {
                this.showToast('error', 'Failed to delete history entry');
            }
        } catch (error) {
            console.error('Error deleting history entry:', error);
            this.showToast('error', 'Network error: ' + error.message);
        }
    }

    async clearHistory() {
        // Confirm with user
        if (!confirm('Are you sure you want to clear all history? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/history`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showToast('success', 'History cleared successfully');
                this.currentHistoryPage = 0;
                this.loadHistory();
            } else {
                this.showToast('error', 'Failed to clear history');
            }
        } catch (error) {
            console.error('Error clearing history:', error);
            this.showToast('error', 'Network error: ' + error.message);
        }
    }

    /* ===================================================================
       SETTINGS MANAGEMENT
       =================================================================== */

    async loadSettings() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/settings`);
            const data = await response.json();

            const settingsForm = document.getElementById('settings-form');
            settingsForm.innerHTML = '';

            // Check if settings is an array
            if (!Array.isArray(data.settings)) {
                console.error('Settings is not an array:', data.settings);
                settingsForm.innerHTML = '<p style="color: var(--text-error);">Error: Invalid settings format</p>';
                return;
            }

            // Group settings by category
            const groupedSettings = {};
            data.settings.forEach(setting => {
                if (!groupedSettings[setting.category]) {
                    groupedSettings[setting.category] = [];
                }
                groupedSettings[setting.category].push(setting);
            });

            // Render each category
            Object.entries(groupedSettings).forEach(([category, settings]) => {
                // Skip provider category (handled in top bar)
                if (category === 'provider') return;

                // Only show API Keys section
                if (category !== 'api_keys') return;

                // Create category section
                const categorySection = document.createElement('div');
                categorySection.className = 'settings-category';

                // Render each setting in the category
                settings.forEach(setting => {
                    const item = document.createElement('div');
                    item.className = 'settings-item';

                    const labelContainer = document.createElement('div');
                    labelContainer.className = 'settings-label-container';

                    const label = document.createElement('label');
                    label.className = 'settings-label';
                    label.textContent = setting.label;
                    label.htmlFor = `setting-${setting.key}`;

                    const description = document.createElement('p');
                    description.className = 'settings-description';
                    description.textContent = setting.description;

                    labelContainer.appendChild(label);
                    labelContainer.appendChild(description);

                    const inputContainer = document.createElement('div');
                    inputContainer.className = 'settings-input-container';

                    // Create input based on type
                    let inputElement;

                    if (setting.type === 'select') {
                        inputElement = document.createElement('select');
                        inputElement.className = 'settings-input';
                        setting.options.forEach(option => {
                            const opt = document.createElement('option');
                            opt.value = option;
                            opt.textContent = option === '' ? 'Auto' : option.charAt(0).toUpperCase() + option.slice(1);
                            if (option === setting.value) opt.selected = true;
                            inputElement.appendChild(opt);
                        });
                    } else if (setting.type === 'checkbox') {
                        inputElement = document.createElement('input');
                        inputElement.type = 'checkbox';
                        inputElement.className = 'settings-checkbox';
                        inputElement.checked = setting.value === 'true';
                    } else if (setting.type === 'password') {
                        inputElement = document.createElement('input');
                        inputElement.type = 'password';
                        inputElement.className = 'settings-input';

                        // If key exists (masked), show as placeholder and keep field empty
                        // User must enter new key to update it
                        if (setting.masked) {
                            inputElement.value = '';
                            inputElement.placeholder = `${setting.value} (current key)`;
                            inputElement.dataset.hasExistingKey = 'true';
                        } else {
                            inputElement.value = '';
                            inputElement.placeholder = 'Enter your API key';
                            inputElement.dataset.hasExistingKey = 'false';
                        }

                        // Add eye icon for password visibility toggle
                        const eyeButton = document.createElement('button');
                        eyeButton.type = 'button';
                        eyeButton.className = 'settings-eye-btn';
                        eyeButton.innerHTML = '👁';
                        eyeButton.title = 'Show/Hide API Key';
                        eyeButton.addEventListener('click', () => {
                            if (inputElement.type === 'password') {
                                inputElement.type = 'text';
                                eyeButton.innerHTML = '👁‍🗨';
                            } else {
                                inputElement.type = 'password';
                                eyeButton.innerHTML = '👁';
                            }
                        });
                        inputContainer.appendChild(eyeButton);
                    } else {
                        inputElement = document.createElement('input');
                        inputElement.type = 'text';
                        inputElement.className = 'settings-input';
                        inputElement.value = setting.value || '';
                    }

                    inputElement.id = `setting-${setting.key}`;
                    inputElement.name = setting.key;

                    // Mark as modified on change
                    inputElement.addEventListener('change', () => {
                        inputElement.dataset.modified = 'true';
                        this.showSaveButton();
                    });

                    inputContainer.insertBefore(inputElement, inputContainer.firstChild);

                    // Add Save & Validate button for API keys
                    if (setting.type === 'password') {
                        // Determine provider from key name
                        const providerMatch = setting.key.match(/^(\w+)_API_KEY$/);
                        const providerName = providerMatch ? providerMatch[1].toLowerCase() : null;

                        // Create button container
                        const buttonContainer = document.createElement('div');
                        buttonContainer.style.display = 'flex';
                        buttonContainer.style.gap = 'var(--space-2)';
                        buttonContainer.style.alignItems = 'center';
                        buttonContainer.style.marginTop = 'var(--space-2)';

                        // Add Save button for individual API key
                        const saveBtn = document.createElement('button');
                        saveBtn.type = 'button';
                        saveBtn.className = 'btn btn-secondary btn-sm';
                        saveBtn.innerHTML = '<span>💾</span><span>Save</span>';
                        saveBtn.style.minWidth = '80px';

                        // Create status container for validation feedback
                        const statusContainer = document.createElement('div');
                        statusContainer.id = `status-${setting.key}`;
                        statusContainer.className = 'validation-status-container';

                        saveBtn.addEventListener('click', async () => {
                            await this.saveAndValidateApiKey(setting.key, inputElement, providerName, statusContainer);
                        });

                        buttonContainer.appendChild(saveBtn);
                        item.appendChild(labelContainer);
                        item.appendChild(inputContainer);
                        item.appendChild(buttonContainer);
                        item.appendChild(statusContainer);
                    } else {
                        item.appendChild(labelContainer);
                        item.appendChild(inputContainer);
                    }

                    categorySection.appendChild(item);
                });

                settingsForm.appendChild(categorySection);
            });

            // Add save button if not present
            if (!document.getElementById('save-settings-btn')) {
                const saveButtonContainer = document.createElement('div');
                saveButtonContainer.className = 'settings-save-container';
                saveButtonContainer.style.display = 'none';

                const saveButton = document.createElement('button');
                saveButton.id = 'save-settings-btn';
                saveButton.className = 'btn btn-primary btn-save-settings';
                saveButton.innerHTML = '<span>💾</span><span>Save All Settings</span>';
                saveButton.addEventListener('click', () => this.saveAllSettings());

                saveButtonContainer.appendChild(saveButton);
                settingsForm.appendChild(saveButtonContainer);
            }

        } catch (error) {
            console.error('Error loading settings:', error);
            this.showToast('error', 'Failed to load settings');
        }
    }

    showSaveButton() {
        const container = document.querySelector('.settings-save-container');
        if (container) {
            container.style.display = 'block';
        }
    }

    async saveAllSettings() {
        const inputs = document.querySelectorAll('[data-modified="true"]');
        let savedCount = 0;
        let errorCount = 0;

        for (const input of inputs) {
            const key = input.name;
            let value;

            if (input.type === 'checkbox') {
                value = input.checked ? 'true' : 'false';
            } else {
                value = input.value;
            }

            try {
                await this.updateSetting(key, value);
                input.removeAttribute('data-modified');
                savedCount++;
            } catch (error) {
                console.error(`Error saving ${key}:`, error);
                errorCount++;
            }
        }

        if (savedCount > 0) {
            this.showToast('success', `Saved ${savedCount} setting(s)`);
        }
        if (errorCount > 0) {
            this.showToast('error', `Failed to save ${errorCount} setting(s)`);
        }

        // Hide save button
        const container = document.querySelector('.settings-save-container');
        if (container) {
            container.style.display = 'none';
        }

        // Reload providers in case they changed
        this.loadProviders();
    }

    async updateSetting(key, value) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/settings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key, value })
            });

            const data = await response.json();

            if (response.ok) {
                this.showToast('success', `Setting "${key}" updated`);
                this.loadProviders();
            } else {
                this.showToast('error', data.detail || 'Failed to update setting');
            }
        } catch (error) {
            console.error('Error updating setting:', error);
            this.showToast('error', 'Network error: ' + error.message);
        }
    }

    async saveAndValidateApiKey(key, inputElement, providerName, statusContainer) {
        const apiKey = inputElement.value.trim();
        const hasExistingKey = inputElement.dataset.hasExistingKey === 'true';

        // If field is empty and there's an existing key, we need to get it from backend to validate
        if (!apiKey && hasExistingKey) {
            // User wants to test existing key without re-entering it
            // We can't validate without the actual key, so just show a message
            this.showToast('info', 'Enter a new API key to save and validate, or use the existing key');
            return;
        }

        if (!apiKey) {
            this.showToast('error', 'Please enter an API key');
            return;
        }

        // Save the API key first
        try {
            await this.updateSetting(key, apiKey);
            // After saving, mark that we now have an existing key and remember the value for quick retries
            inputElement.dataset.hasExistingKey = 'true';
            inputElement.dataset.lastSavedKey = apiKey;
            // Clear the field and update placeholder
            const maskedKey = '●'.repeat(Math.max(0, apiKey.length - 4)) + apiKey.slice(-4);
            inputElement.value = '';
            inputElement.placeholder = `${maskedKey} (current key)`;
        } catch (error) {
            this.showToast('error', 'Failed to save API key');
            return;
        }

        // Now validate the connection if provider is known
        if (!providerName) {
            this.showToast('success', 'API key saved');
            return;
        }

        await this.validateApiKey(providerName, apiKey, key, inputElement, statusContainer);
    }

    async validateApiKey(provider, apiKey, settingKey, inputElement, statusContainer) {
        // Show validating status
        inputElement.classList.remove('valid', 'invalid');
        inputElement.classList.add('validating');

        statusContainer.innerHTML = `
            <div class="validation-status validating">
                <span class="validation-status-icon">⚗</span>
                <span class="validation-status-text">Verifying connection...</span>
            </div>
        `;

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/settings/validate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider, api_key: apiKey })
            });

            const data = await response.json();

            inputElement.classList.remove('validating');

            if (data.valid) {
                // Success state
                inputElement.classList.add('valid');

                const modelsInfo = data.models_available && data.models_available.length > 0
                    ? `<div style="margin-top: var(--space-1); font-size: var(--text-xs); opacity: 0.8;">Models: ${data.models_available.slice(0, 3).join(', ')}${data.models_available.length > 3 ? '...' : ''}</div>`
                    : '';

                statusContainer.innerHTML = `
                    <div class="validation-status success">
                        <span class="validation-status-icon">✓</span>
                        <span class="validation-status-text">Connected to ${provider}</span>
                        <span class="validation-status-time">Just now</span>
                    </div>
                    ${modelsInfo}
                `;

                this.showToast('success', `✓ ${provider} API key validated`);
            } else {
                // Error state
                inputElement.classList.add('invalid');

                statusContainer.innerHTML = `
                    <div class="validation-status error">
                        <span class="validation-status-icon">✗</span>
                        <span class="validation-status-text">Connection Failed</span>
                    </div>
                    <div class="validation-error-details">
                        <strong>Error:</strong> ${this.escapeHtml(data.error || 'Unknown error')}<br>
                        <strong>Suggestion:</strong> ${this.escapeHtml(data.suggestion || 'Check your API key and try again')}
                    </div>
                    <button class="validation-retry-btn" onclick="window.promptheusApp.retryValidation('${provider}', '${settingKey}')">
                        ↻ Retry
                    </button>
                `;

                this.showToast('error', `✗ ${provider} validation failed`);
            }
        } catch (error) {
            inputElement.classList.remove('validating');
            inputElement.classList.add('invalid');

            statusContainer.innerHTML = `
                <div class="validation-status error">
                    <span class="validation-status-icon">✗</span>
                    <span class="validation-status-text">Validation Error</span>
                </div>
                <div class="validation-error-details">
                    Network error: ${this.escapeHtml(error.message)}
                </div>
            `;

            this.showToast('error', 'Network error during validation');
        }
    }

    retryValidation(provider, settingKey) {
        const inputElement = document.getElementById(`setting-${settingKey}`);
        const statusContainer = document.getElementById(`status-${settingKey}`);

        if (!inputElement || !statusContainer) {
            this.showToast('error', 'Unable to retry validation—input not found');
            return;
        }

        let apiKey = inputElement.value.trim();
        if (!apiKey) {
            apiKey = inputElement.dataset.lastSavedKey || '';
        }

        if (!apiKey) {
            this.showToast('info', 'Enter an API key to validate');
            return;
        }

        this.validateApiKey(provider, apiKey, settingKey, inputElement, statusContainer);
    }

    /* ===================================================================
       PROMPT TWEAKING
       =================================================================== */

    async showTweakPromptDialog() {
        const outputDiv = document.getElementById('output');
        const optimizedPromptDiv = outputDiv.querySelector('.optimized-prompt-content');

        if (!optimizedPromptDiv) {
            this.showMessage('error', 'No prompt to tweak');
            return;
        }

        const currentPrompt = optimizedPromptDiv.textContent || optimizedPromptDiv.innerText;

        // Show tweak input form
        let formHtml = '<div class="tweak-container">';
        formHtml += '<div class="tweak-header">';
        formHtml += '<h3 class="tweak-title">Tweak Your Prompt</h3>';
        formHtml += '<p class="tweak-description">Describe how you want to modify the optimized prompt:</p>';
        formHtml += '</div>';
        formHtml += '<form id="tweak-form">';
        formHtml += '<div class="tweak-item">';
        formHtml += '<textarea id="tweak-instruction" placeholder="e.g., Make it more formal, Add more details about X, Make it shorter" required class="tweak-input"></textarea>';
        formHtml += '</div>';
        formHtml += '<div class="tweak-examples">';
        formHtml += '<p style="font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-2);">Examples:</p>';
        formHtml += '<ul style="font-size: var(--text-sm); color: var(--text-secondary); margin-left: var(--space-4);">';
        formHtml += '<li>Make it more formal and professional</li>';
        formHtml += '<li>Add specific examples for each point</li>';
        formHtml += '<li>Make it more concise and direct</li>';
        formHtml += '<li>Convert to bullet points</li>';
        formHtml += '</ul>';
        formHtml += '</div>';
        formHtml += '<div class="tweak-actions">';
        formHtml += '<button type="submit" class="btn btn-primary">Apply Tweak</button>';
        formHtml += '<button type="button" id="cancel-tweak-btn" class="btn btn-secondary">Cancel</button>';
        formHtml += '</div>';
        formHtml += '</form></div>';

        outputDiv.innerHTML = formHtml;

        const form = document.getElementById('tweak-form');
        const cancelBtn = document.getElementById('cancel-tweak-btn');
        const tweakBtn = document.getElementById('tweak-btn');
        const copyBtn = document.getElementById('copy-btn');

        tweakBtn.classList.add('hidden'); // Hide tweak button while tweaking
        copyBtn.classList.add('hidden'); // Hide copy button while tweaking

        cancelBtn.addEventListener('click', () => {
            // Restore the original prompt
            outputDiv.innerHTML = `<div class="optimized-prompt-content">${this.escapeHtml(currentPrompt)}</div>`;
            tweakBtn.classList.remove('hidden');
            copyBtn.classList.remove('hidden');
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const tweakInstruction = document.getElementById('tweak-instruction').value.trim();

            if (!tweakInstruction) {
                this.showMessage('error', 'Please enter a tweak instruction');
                return;
            }

            const submitButton = form.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner"></span><span>Applying tweak...</span>';

            try {
                const provider = document.getElementById('provider-select').value;
                const response = await fetch(`${this.apiBaseUrl}/api/prompt/tweak`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        current_prompt: currentPrompt,
                        tweak_instruction: tweakInstruction,
                        provider: provider || null
                    })
                });

                const data = await response.json();

                if (data.success) {
                    this.currentOptimizedPrompt = data.tweaked_prompt;
                    this.renderOutput();
                    tweakBtn.classList.remove('hidden');
                    copyBtn.classList.remove('hidden');
                } else {
                    this.showMessage('error', data.error || 'Failed to tweak prompt');
                }
            } catch (error) {
                console.error('Error tweaking prompt:', error);
                this.showMessage('error', 'Network error: ' + error.message);
            } finally {
                submitButton.disabled = false;
                submitButton.innerHTML = '<span>Apply Tweak</span>';
            }
        });
    }

    /* ===================================================================
       UI HELPERS
       =================================================================== */

    async copyOutputToClipboard() {
        const outputDiv = document.getElementById('output');
        const optimizedPromptDiv = outputDiv.querySelector('.optimized-prompt-content');

        if (!optimizedPromptDiv) {
            this.showToast('info', 'Nothing to copy');
            return;
        }

        const textToCopy = optimizedPromptDiv.textContent || optimizedPromptDiv.innerText;

        try {
            await navigator.clipboard.writeText(textToCopy);
            this.showToast('success', 'Copied to clipboard!');
        } catch (err) {
            console.error('Failed to copy:', err);

            // Fallback
            const textArea = document.createElement('textarea');
            textArea.value = textToCopy;
            textArea.style.position = 'fixed';
            textArea.style.opacity = '0';
            document.body.appendChild(textArea);
            textArea.select();

            try {
                const successful = document.execCommand('copy');
                document.body.removeChild(textArea);

                if (successful) {
                    this.showToast('success', 'Copied to clipboard!');
                } else {
                    this.showToast('error', 'Failed to copy');
                }
            } catch (err) {
                document.body.removeChild(textArea);
                this.showToast('error', 'Failed to copy');
            }
        }
    }

    showToast(type, message) {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const iconMap = {
            success: '✓',
            error: '⚠',
            info: '💡'
        };

        toast.innerHTML = `
            <span class="toast-icon">${iconMap[type]}</span>
            <span class="toast-message">${this.escapeHtml(message)}</span>
        `;

        document.body.appendChild(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);

        // Remove after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    showMessage(type, message) {
        const outputDiv = document.getElementById('output');
        const iconMap = {
            success: '✓',
            error: '⚠',
            info: '💡'
        };

        outputDiv.innerHTML = `
            <p class="message message-${type}">
                <span>${iconMap[type]}</span>
                <span>${this.escapeHtml(message)}</span>
            </p>
        `;
    }

    showProgressIndicator(phase) {
        const outputDiv = document.getElementById('output');
        const phases = {
            analyzing: {
                symbol: '🔮',
                text: 'Analyzing prompt...'
            },
            generating_questions: {
                symbol: '❓',
                text: 'Generating questions...'
            },
            optimizing: {
                symbol: '⚗',
                text: 'Optimizing...'
            },
            refining: {
                symbol: '✨',
                text: 'Refining with your answers...'
            }
        };

        const phaseData = phases[phase] || phases.optimizing;

        outputDiv.innerHTML = `
            <div class="progress-indicator">
                <div class="progress-symbol">${phaseData.symbol}</div>
                <div class="progress-text">${phaseData.text}</div>
            </div>
        `;
    }

    escapeHtml(text) {
        if (typeof text !== 'string') return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.promptheusApp = new PromptheusApp();
});
