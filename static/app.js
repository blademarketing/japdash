class SocialMediaManager {
    constructor() {
        this.accounts = [];
        this.currentEditId = null;
        this.currentActionAccount = null;
        this.japServices = {};
        this.allServices = []; // Flat array for search functionality
        this.quickAllServices = []; // For quick action search
        this.japBalance = null;
        this.currentTab = 'accounts';
        this.historyData = {
            executions: [],
            total: 0,
            offset: 0,
            limit: 20
        };
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadAccounts();
        this.loadJAPBalance();
    }

    bindEvents() {
        // Account modal events
        document.getElementById('addBtn').addEventListener('click', () => this.openModal());
        document.getElementById('closeModal').addEventListener('click', () => this.closeModal());
        document.getElementById('cancelBtn').addEventListener('click', () => this.closeModal());
        document.getElementById('accountForm').addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Action modal events
        document.getElementById('closeActionModal').addEventListener('click', () => this.closeActionModal());
        document.getElementById('cancelActionBtn').addEventListener('click', () => this.closeActionModal());
        document.getElementById('actionConfigForm').addEventListener('submit', (e) => this.handleActionSubmit(e));
        
        // Quick execute modal events
        document.getElementById('quickExecuteBtn').addEventListener('click', () => this.openQuickExecuteModal());
        document.getElementById('closeQuickExecuteModal').addEventListener('click', () => this.closeQuickExecuteModal());
        document.getElementById('cancelQuickExecuteBtn').addEventListener('click', () => this.closeQuickExecuteModal());
        document.getElementById('quickExecuteForm').addEventListener('submit', (e) => this.handleQuickExecuteSubmit(e));
        
        // Dynamic action form events
        document.getElementById('actionType').addEventListener('change', (e) => this.onActionTypeChange(e));
        document.getElementById('japService').addEventListener('change', (e) => this.onServiceChange(e));
        document.getElementById('serviceSearch').addEventListener('input', (e) => this.onServiceSearch(e));
        document.getElementById('serviceSearch').addEventListener('focus', (e) => this.showServiceDropdown());
        document.getElementById('serviceSearch').addEventListener('blur', (e) => this.hideServiceDropdown(e));
        
        // Quick execute form events
        document.getElementById('quickPlatform').addEventListener('change', (e) => this.onQuickPlatformChange(e));
        document.getElementById('quickActionType').addEventListener('change', (e) => this.onQuickActionTypeChange(e));
        document.getElementById('quickJapService').addEventListener('change', (e) => this.onQuickServiceChange(e));
        document.getElementById('quickServiceSearch').addEventListener('input', (e) => this.onQuickServiceSearch(e));
        document.getElementById('quickServiceSearch').addEventListener('focus', (e) => this.showQuickServiceDropdown());
        document.getElementById('quickServiceSearch').addEventListener('blur', (e) => this.hideQuickServiceDropdown(e));
        
        // Tab events
        document.getElementById('accountsTab').addEventListener('click', () => this.switchTab('accounts'));
        document.getElementById('historyTab').addEventListener('click', () => this.switchTab('history'));
        
        // History events
        document.getElementById('applyFilters').addEventListener('click', () => this.loadHistory());
        document.getElementById('historyPrevBtn').addEventListener('click', () => this.historyPrevPage());
        document.getElementById('historyNextBtn').addEventListener('click', () => this.historyNextPage());
        
        // Close modals when clicking outside
        document.getElementById('modal').addEventListener('click', (e) => {
            if (e.target.id === 'modal') this.closeModal();
        });
        
        document.getElementById('actionModal').addEventListener('click', (e) => {
            if (e.target.id === 'actionModal') this.closeActionModal();
        });
        
        document.getElementById('quickExecuteModal').addEventListener('click', (e) => {
            if (e.target.id === 'quickExecuteModal') this.closeQuickExecuteModal();
        });
    }

    async loadAccounts() {
        try {
            const response = await fetch('/api/accounts');
            this.accounts = await response.json();
            this.renderTable();
        } catch (error) {
            console.error('Error loading accounts:', error);
        }
    }

    async loadJAPBalance() {
        try {
            const response = await fetch('/api/jap/balance');
            this.japBalance = await response.json();
            if (this.japBalance && !this.japBalance.error) {
                const balanceEl = document.getElementById('balanceAmount');
                const quickBalanceEl = document.getElementById('quickBalanceAmount');
                if (balanceEl) {
                    balanceEl.textContent = `$${this.japBalance.balance} ${this.japBalance.currency}`;
                }
                if (quickBalanceEl) {
                    quickBalanceEl.textContent = `$${this.japBalance.balance} ${this.japBalance.currency}`;
                }
            }
        } catch (error) {
            console.error('Error loading JAP balance:', error);
        }
    }

    renderTable() {
        const tbody = document.getElementById('accountsTable');
        const emptyState = document.getElementById('emptyState');
        
        if (this.accounts.length === 0) {
            tbody.innerHTML = '';
            emptyState.classList.remove('hidden');
            return;
        }
        
        emptyState.classList.add('hidden');
        
        tbody.innerHTML = this.accounts.map(account => `
            <tr class="hover:bg-gray-50">
                <td class="px-4 py-3">
                    <div class="flex items-center gap-2">
                        <i class="${this.getPlatformIcon(account.platform)} text-lg"></i>
                        <span class="font-medium">${account.platform}</span>
                    </div>
                </td>
                <td class="px-4 py-3 text-gray-700">${account.username}</td>
                <td class="px-4 py-3 text-gray-700">${account.display_name || '-'}</td>
                <td class="px-4 py-3">
                    ${account.url ? `<a href="${account.url}" target="_blank" class="text-blue-500 hover:text-blue-700 underline">View Profile</a>` : '-'}
                </td>
                <td class="px-4 py-3">
                    ${this.renderRSSStatus(account)}
                </td>
                <td class="px-4 py-3">
                    <button onclick="app.openActionModal(${account.id})" class="bg-purple-500 hover:bg-purple-600 text-white px-3 py-1 rounded text-sm transition-colors">
                        <i class="fas fa-rss mr-1"></i>
                        Setup
                    </button>
                </td>
                <td class="px-4 py-3">
                    <div class="flex gap-2">
                        <button onclick="app.editAccount(${account.id})" class="text-blue-500 hover:text-blue-700 p-1">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button onclick="app.deleteAccount(${account.id})" class="text-red-500 hover:text-red-700 p-1">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    getPlatformIcon(platform) {
        const icons = {
            'Instagram': 'fab fa-instagram text-pink-500',
            'Facebook': 'fab fa-facebook text-blue-600',
            'X': 'fab fa-x-twitter text-black',
            'TikTok': 'fab fa-tiktok text-black'
        };
        return icons[platform] || 'fas fa-globe';
    }

    renderRSSStatus(account) {
        const status = account.rss_status || 'pending';
        
        switch (status) {
            case 'active':
                const lastPost = account.rss_last_post ? 
                    new Date(account.rss_last_post).toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric', 
                        hour: '2-digit',
                        minute: '2-digit'
                    }) : 'Unknown';
                return `
                    <div class="flex flex-col gap-1">
                        <div class="flex items-center gap-2">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                <i class="fas fa-check-circle mr-1"></i>
                                Active
                            </span>
                            <button onclick="app.refreshRSSStatus(${account.id})" class="text-blue-500 hover:text-blue-700 text-xs" title="Refresh Status">
                                <i class="fas fa-sync-alt"></i>
                            </button>
                        </div>
                        ${account.rss_feed_url ? `
                            <a href="${account.rss_feed_url}" target="_blank" class="text-xs text-blue-500 hover:text-blue-700 underline" title="View RSS Feed">
                                <i class="fas fa-rss mr-1"></i>Live Feed
                            </a>
                        ` : ''}
                        <div class="text-xs text-gray-500">Last: ${lastPost}</div>
                    </div>
                `;
            
            case 'failed':
                return `
                    <div class="flex flex-col gap-1">
                        <div class="flex items-center gap-2">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                <i class="fas fa-exclamation-triangle mr-1"></i>
                                Failed
                            </span>
                            <button onclick="app.retryRSSFeed(${account.id})" class="text-orange-500 hover:text-orange-700 text-xs" title="Retry RSS Creation">
                                <i class="fas fa-redo"></i>
                            </button>
                        </div>
                        <div class="text-xs text-gray-500">RSS creation failed</div>
                    </div>
                `;
            
            case 'pending':
                return `
                    <div class="flex flex-col gap-1">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                            <i class="fas fa-clock mr-1"></i>
                            Pending
                        </span>
                        <div class="text-xs text-gray-500">Setting up RSS...</div>
                    </div>
                `;
            
            case 'disabled':
                return `
                    <div class="flex flex-col gap-1">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            <i class="fas fa-pause mr-1"></i>
                            Disabled
                        </span>
                        <button onclick="app.retryRSSFeed(${account.id})" class="text-blue-500 hover:text-blue-700 text-xs" title="Enable RSS Feed">
                            <i class="fas fa-play mr-1"></i>Enable
                        </button>
                    </div>
                `;
            
            default:
                return `
                    <div class="flex flex-col gap-1">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            <i class="fas fa-question mr-1"></i>
                            Unknown
                        </span>
                        <button onclick="app.retryRSSFeed(${account.id})" class="text-blue-500 hover:text-blue-700 text-xs" title="Setup RSS Feed">
                            <i class="fas fa-rss mr-1"></i>Setup
                        </button>
                    </div>
                `;
        }
    }

    // Account modal methods
    openModal(account = null) {
        const modal = document.getElementById('modal');
        const modalTitle = document.getElementById('modalTitle');
        const form = document.getElementById('accountForm');
        
        if (account) {
            modalTitle.textContent = 'Edit Account';
            document.getElementById('accountId').value = account.id;
            document.getElementById('platform').value = account.platform;
            document.getElementById('username').value = account.username;
            document.getElementById('displayName').value = account.display_name || '';
            document.getElementById('url').value = account.url || '';
            this.currentEditId = account.id;
        } else {
            modalTitle.textContent = 'Add Account';
            form.reset();
            document.getElementById('accountId').value = '';
            this.currentEditId = null;
        }
        
        modal.classList.remove('hidden');
    }

    closeModal() {
        const modal = document.getElementById('modal');
        modal.classList.add('hidden');
        document.getElementById('accountForm').reset();
        this.currentEditId = null;
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        // Get submit button and disable it
        const submitButton = e.target.querySelector('button[type="submit"]');
        const originalText = submitButton.innerHTML;
        
        // Disable button and show loading state
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
        submitButton.classList.add('opacity-75', 'cursor-not-allowed');
        
        const formData = {
            platform: document.getElementById('platform').value,
            username: document.getElementById('username').value,
            display_name: document.getElementById('displayName').value,
            url: document.getElementById('url').value
        };

        try {
            let response;
            if (this.currentEditId) {
                response = await fetch(`/api/accounts/${this.currentEditId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
            } else {
                response = await fetch('/api/accounts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
            }

            if (response.ok) {
                this.closeModal();
                this.loadAccounts();
                this.showNotification(this.currentEditId ? 'Account updated successfully!' : 'Account added successfully!', 'success');
            } else {
                const error = await response.json();
                this.showNotification(error.error || 'An error occurred', 'error');
            }
        } catch (error) {
            console.error('Error saving account:', error);
            this.showNotification('An error occurred while saving the account', 'error');
        } finally {
            // Re-enable button and restore original text
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
            submitButton.classList.remove('opacity-75', 'cursor-not-allowed');
        }
    }

    // Action modal methods
    async openActionModal(accountId) {
        const account = this.accounts.find(acc => acc.id === accountId);
        if (!account) return;

        this.currentActionAccount = account;
        
        // Update account info display
        document.getElementById('actionAccountInfo').innerHTML = `
            <div class="flex items-center gap-3">
                <i class="${this.getPlatformIcon(account.platform)} text-2xl"></i>
                <div>
                    <h4 class="font-semibold">${account.platform} - ${account.username}</h4>
                    <p class="text-sm text-gray-600">${account.display_name || 'No display name'}</p>
                </div>
            </div>
        `;

        document.getElementById('actionAccountId').value = accountId;
        
        // Load JAP services for this platform
        await this.loadJAPServices(account.platform);
        
        // Load existing actions
        await this.loadAccountActions(accountId);
        
        // Show modal
        document.getElementById('actionModal').classList.remove('hidden');
    }

    closeActionModal() {
        document.getElementById('actionModal').classList.add('hidden');
        this.currentActionAccount = null;
        document.getElementById('actionConfigForm').reset();
        this.clearDynamicParameters();
    }

    async loadJAPServices(platform) {
        try {
            const response = await fetch(`/api/jap/services/${platform}`);
            this.japServices = await response.json();
            
            if (this.japServices.error) {
                this.showNotification(`Error loading services: ${this.japServices.error}`, 'error');
                return;
            }

            this.populateActionTypes();
        } catch (error) {
            console.error('Error loading JAP services:', error);
            this.showNotification('Error loading JAP services', 'error');
        }
    }

    populateActionTypes() {
        const actionTypeSelect = document.getElementById('actionType');
        actionTypeSelect.innerHTML = '<option value="">Select Action Type</option>';
        
        Object.keys(this.japServices).forEach(actionType => {
            const option = document.createElement('option');
            option.value = actionType;
            option.textContent = this.formatActionType(actionType);
            actionTypeSelect.appendChild(option);
        });
    }

    formatActionType(actionType) {
        return actionType.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    onActionTypeChange(e) {
        const actionType = e.target.value;
        const serviceSelect = document.getElementById('japService');
        const searchInput = document.getElementById('serviceSearch');
        
        serviceSelect.innerHTML = '<option value="">Select Service</option>';
        searchInput.value = '';
        document.getElementById('serviceDetails').classList.add('hidden');
        document.getElementById('serviceDropdown').classList.add('hidden');
        this.clearDynamicParameters();

        // Populate allServices array for current action type
        this.allServices = [];
        if (actionType && this.japServices[actionType]) {
            this.allServices = this.japServices[actionType].map(service => ({
                ...service,
                display_text: `ID: ${service.service_id} - ${service.name} - $${service.rate}/1k`,
                value: JSON.stringify({
                    service_id: service.service_id,
                    name: service.name,
                    rate: service.rate,
                    min_quantity: service.min_quantity,
                    max_quantity: service.max_quantity,
                    description: service.description
                })
            }));
            
            // Also populate the hidden select for backward compatibility
            this.allServices.forEach(service => {
                const option = document.createElement('option');
                option.value = service.value;
                option.textContent = service.display_text;
                serviceSelect.appendChild(option);
            });
        }
    }

    onServiceChange(e) {
        const serviceData = e.target.value;
        const detailsDiv = document.getElementById('serviceDetails');
        
        if (serviceData) {
            const service = JSON.parse(serviceData);
            detailsDiv.innerHTML = `
                <div class="text-sm">
                    <p><strong>Service:</strong> ${service.name}</p>
                    <p><strong>Rate:</strong> $${service.rate} per 1000</p>
                    <p><strong>Min Quantity:</strong> ${service.min_quantity}</p>
                    <p><strong>Max Quantity:</strong> ${service.max_quantity}</p>
                    ${service.description ? `<p><strong>Description:</strong> ${service.description}</p>` : ''}
                </div>
            `;
            detailsDiv.classList.remove('hidden');
            this.generateDynamicParameters(service);
        } else {
            detailsDiv.classList.add('hidden');
            this.clearDynamicParameters();
        }
    }

    generateDynamicParameters(service) {
        const container = document.getElementById('dynamicParameters');
        container.innerHTML = '';

        // Quantity parameter (always present)
        const quantityDiv = document.createElement('div');
        quantityDiv.innerHTML = `
            <label class="block text-sm font-medium text-gray-700 mb-2">Quantity</label>
            <input type="number" id="param_quantity" required 
                   min="${service.min_quantity}" max="${service.max_quantity}" 
                   value="${service.min_quantity}"
                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
            <p class="text-xs text-gray-500 mt-1">Min: ${service.min_quantity}, Max: ${service.max_quantity}</p>
            <p class="text-xs text-blue-600">Estimated cost: $<span id="estimatedCost">0.00</span></p>
        `;
        container.appendChild(quantityDiv);

        // Add cost calculation
        const quantityInput = quantityDiv.querySelector('#param_quantity');
        quantityInput.addEventListener('input', (e) => {
            const quantity = parseInt(e.target.value) || 0;
            const cost = (quantity / 1000) * service.rate;
            document.getElementById('estimatedCost').textContent = cost.toFixed(2);
        });

        // Trigger initial calculation
        quantityInput.dispatchEvent(new Event('input'));

        // Additional parameters based on service type
        if (service.name.toLowerCase().includes('comment')) {
            const commentsDiv = document.createElement('div');
            commentsDiv.innerHTML = `
                <label class="block text-sm font-medium text-gray-700 mb-2">Custom Comments</label>
                <textarea id="param_custom_comments" rows="4" 
                          placeholder="Enter custom comments (one per line)"
                          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"></textarea>
                <p class="text-xs text-gray-500 mt-1">Leave empty for random comments</p>
            `;
            container.appendChild(commentsDiv);
        }

        // Trigger configuration info
        const triggerInfoDiv = document.createElement('div');
        triggerInfoDiv.innerHTML = `
            <div class="p-3 bg-blue-50 rounded-lg text-sm">
                <i class="fas fa-info-circle text-blue-600 mr-2"></i>
                <span class="text-blue-800">This action will be triggered automatically when new posts are detected via RSS feeds.</span>
            </div>
        `;
        container.appendChild(triggerInfoDiv);
    }

    clearDynamicParameters() {
        document.getElementById('dynamicParameters').innerHTML = '';
    }

    onServiceSearch(e) {
        const query = e.target.value.toLowerCase().trim();
        const dropdown = document.getElementById('serviceDropdown');
        
        if (!query || this.allServices.length === 0) {
            dropdown.classList.add('hidden');
            return;
        }

        // Filter services by ID or name
        const filteredServices = this.allServices.filter(service => {
            const searchTerms = [
                service.service_id.toString(),
                service.name.toLowerCase(),
                service.display_text.toLowerCase()
            ];
            return searchTerms.some(term => term.includes(query));
        });

        if (filteredServices.length === 0) {
            dropdown.innerHTML = '<div class="p-3 text-gray-500 text-sm">No services found</div>';
        } else {
            dropdown.innerHTML = filteredServices.slice(0, 10).map(service => `
                <div class="p-3 hover:bg-gray-100 cursor-pointer border-b last:border-b-0" 
                     onclick="app.selectService('${service.service_id}')">
                    <div class="font-medium text-sm">ID: ${service.service_id}</div>
                    <div class="text-gray-600 text-xs">${service.name}</div>
                    <div class="text-blue-600 text-xs">$${service.rate}/1k | Min: ${service.min_quantity} | Max: ${service.max_quantity}</div>
                </div>
            `).join('');
        }

        dropdown.classList.remove('hidden');
    }

    showServiceDropdown() {
        if (this.allServices.length > 0) {
            const searchInput = document.getElementById('serviceSearch');
            if (searchInput.value.trim()) {
                this.onServiceSearch({ target: searchInput });
            }
        }
    }

    hideServiceDropdown(e) {
        // Delay hiding to allow clicks on dropdown items
        setTimeout(() => {
            document.getElementById('serviceDropdown').classList.add('hidden');
        }, 200);
    }

    selectService(serviceId) {
        const service = this.allServices.find(s => s.service_id.toString() === serviceId.toString());
        if (service) {
            const searchInput = document.getElementById('serviceSearch');
            const serviceSelect = document.getElementById('japService');
            
            // Update search input display
            searchInput.value = `ID: ${service.service_id} - ${service.name}`;
            
            // Update hidden select
            serviceSelect.value = service.value;
            
            // Hide dropdown
            document.getElementById('serviceDropdown').classList.add('hidden');
            
            // Trigger service change event
            this.onServiceChange({ target: serviceSelect });
        }
    }

    async handleActionSubmit(e) {
        e.preventDefault();
        
        // Get submit button and disable it
        const submitButton = e.target.querySelector('button[type="submit"]');
        const originalText = submitButton.innerHTML;
        
        const serviceData = document.getElementById('japService').value;
        const searchInput = document.getElementById('serviceSearch').value;
        
        if (!serviceData || !searchInput.trim()) {
            this.showNotification('Please select a service using the search box', 'error');
            return;
        }

        // Disable button and show loading state
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Configuring...';
        submitButton.classList.add('opacity-75', 'cursor-not-allowed');

        const service = JSON.parse(serviceData);
        const parameters = {
            quantity: parseInt(document.getElementById('param_quantity').value),
        };

        // Add optional parameters
        const customComments = document.getElementById('param_custom_comments');
        if (customComments && customComments.value.trim()) {
            parameters.custom_comments = customComments.value.trim();
        }

        const actionData = {
            action_type: document.getElementById('actionType').value,
            jap_service_id: service.service_id,
            service_name: service.name,
            parameters: parameters
        };

        try {
            const accountId = document.getElementById('actionAccountId').value;
            const response = await fetch(`/api/accounts/${accountId}/actions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(actionData)
            });

            if (response.ok) {
                const result = await response.json();
                this.showNotification('Action configured successfully! It will be triggered by RSS feed updates.', 'success');
                
                // Reload actions list
                await this.loadAccountActions(accountId);
                
                // Reset form
                document.getElementById('actionConfigForm').reset();
                this.clearDynamicParameters();
            } else {
                const error = await response.json();
                this.showNotification(error.error || 'Error configuring action', 'error');
            }
        } catch (error) {
            console.error('Error configuring action:', error);
            this.showNotification('Error configuring action', 'error');
        } finally {
            // Re-enable button and restore original text
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
            submitButton.classList.remove('opacity-75', 'cursor-not-allowed');
        }
    }

    async loadAccountActions(accountId) {
        try {
            const response = await fetch(`/api/accounts/${accountId}/actions`);
            const actions = await response.json();
            
            const container = document.getElementById('actionsList');
            
            if (actions.length === 0) {
                container.innerHTML = '<p class="text-gray-500 text-sm">No actions configured yet</p>';
                return;
            }

            container.innerHTML = actions.map(action => `
                <div class="flex items-center justify-between p-3 bg-white border rounded-lg">
                    <div class="flex-1">
                        <div class="flex items-center gap-2">
                            <span class="font-medium">${this.formatActionType(action.action_type)}</span>
                            <span class="text-sm text-gray-500">•</span>
                            <span class="text-sm text-gray-600">${action.service_name}</span>
                        </div>
                        <div class="text-xs text-gray-500 mt-1">
                            Quantity: ${action.parameters.quantity} | Triggered: ${action.order_count || 0} times | Completed: ${action.completed_orders || 0}
                        </div>
                        <div class="text-xs text-blue-600 mt-1">
                            <i class="fas fa-rss mr-1"></i>RSS Trigger Ready
                        </div>
                    </div>
                    <div class="flex gap-2">
                        <button onclick="app.deleteAction(${action.id})" class="bg-red-500 hover:bg-red-600 text-white px-2 py-1 rounded text-xs">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Error loading actions:', error);
        }
    }

    async executeAction(actionId) {
        try {
            const response = await fetch(`/api/actions/${actionId}/execute`, {
                method: 'POST'
            });

            if (response.ok) {
                const result = await response.json();
                this.showNotification(`Action executed! Order ID: ${result.order_id}`, 'success');
                
                // Reload actions to update order count
                if (this.currentActionAccount) {
                    await this.loadAccountActions(this.currentActionAccount.id);
                }
            } else {
                const error = await response.json();
                this.showNotification(error.error || 'Error executing action', 'error');
            }
        } catch (error) {
            console.error('Error executing action:', error);
            this.showNotification('Error executing action', 'error');
        }
    }

    async deleteAction(actionId) {
        if (!confirm('Are you sure you want to delete this action?')) return;

        try {
            const response = await fetch(`/api/actions/${actionId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showNotification('Action deleted successfully!', 'success');
                
                // Reload actions
                if (this.currentActionAccount) {
                    await this.loadAccountActions(this.currentActionAccount.id);
                }
            } else {
                this.showNotification('Error deleting action', 'error');
            }
        } catch (error) {
            console.error('Error deleting action:', error);
            this.showNotification('Error deleting action', 'error');
        }
    }

    // Quick Execute Modal Methods
    openQuickExecuteModal() {
        document.getElementById('quickExecuteModal').classList.remove('hidden');
        // Reset form
        document.getElementById('quickExecuteForm').reset();
        document.getElementById('quickServiceSearch').disabled = true;
        document.getElementById('quickServiceSearch').placeholder = "First select action type...";
        this.clearQuickDynamicParameters();
    }

    closeQuickExecuteModal() {
        document.getElementById('quickExecuteModal').classList.add('hidden');
        document.getElementById('quickExecuteForm').reset();
        this.clearQuickDynamicParameters();
    }

    async onQuickPlatformChange(e) {
        const platform = e.target.value;
        const actionTypeSelect = document.getElementById('quickActionType');
        const serviceSearch = document.getElementById('quickServiceSearch');
        
        // Reset dependent fields
        actionTypeSelect.innerHTML = '<option value="">Select Action Type</option>';
        serviceSearch.disabled = true;
        serviceSearch.value = '';
        serviceSearch.placeholder = "First select action type...";
        this.clearQuickDynamicParameters();
        
        if (!platform) {
            actionTypeSelect.innerHTML = '<option value="">First select a platform</option>';
            return;
        }

        try {
            // Load services for the selected platform
            const response = await fetch(`/api/jap/services/${platform}`);
            const services = await response.json();
            
            if (services.error) {
                this.showNotification(`Error loading services: ${services.error}`, 'error');
                return;
            }

            // Populate action types
            Object.keys(services).forEach(actionType => {
                const option = document.createElement('option');
                option.value = actionType;
                option.textContent = this.formatActionType(actionType);
                actionTypeSelect.appendChild(option);
            });

            // Store services for quick access
            this.japServices = services;
        } catch (error) {
            console.error('Error loading JAP services:', error);
            this.showNotification('Error loading JAP services', 'error');
        }
    }

    onQuickActionTypeChange(e) {
        const actionType = e.target.value;
        const serviceSelect = document.getElementById('quickJapService');
        const searchInput = document.getElementById('quickServiceSearch');
        const urlHelpText = document.getElementById('urlHelpText');
        
        serviceSelect.innerHTML = '<option value="">Select Service</option>';
        searchInput.value = '';
        document.getElementById('quickServiceDetails').classList.add('hidden');
        document.getElementById('quickServiceDropdown').classList.add('hidden');
        this.clearQuickDynamicParameters();

        if (!actionType) {
            searchInput.disabled = true;
            searchInput.placeholder = "First select action type...";
            urlHelpText.textContent = "Select a service first";
            return;
        }

        // Enable service search
        searchInput.disabled = false;
        searchInput.placeholder = "Type service ID (e.g. 1234) or search by name...";

        // Update URL help text based on action type
        this.updateUrlHelpText(actionType);

        // Populate quickAllServices array for current action type
        this.quickAllServices = [];
        if (actionType && this.japServices[actionType]) {
            this.quickAllServices = this.japServices[actionType].map(service => ({
                ...service,
                display_text: `ID: ${service.service_id} - ${service.name} - $${service.rate}/1k`,
                value: JSON.stringify({
                    service_id: service.service_id,
                    name: service.name,
                    rate: service.rate,
                    min_quantity: service.min_quantity,
                    max_quantity: service.max_quantity,
                    description: service.description
                })
            }));
            
            // Also populate the hidden select for backward compatibility
            this.quickAllServices.forEach(service => {
                const option = document.createElement('option');
                option.value = service.value;
                option.textContent = service.display_text;
                serviceSelect.appendChild(option);
            });
        }
    }

    updateUrlHelpText(actionType) {
        const urlHelpText = document.getElementById('urlHelpText');
        const targetUrlInput = document.getElementById('quickTargetUrl');
        
        const helpTexts = {
            'followers': 'Profile page URL (e.g., https://instagram.com/username)',
            'likes': 'Post URL (e.g., https://instagram.com/p/ABC123/)',
            'views': 'Post/video URL (e.g., https://youtube.com/watch?v=ABC123)',
            'comments': 'Post URL (e.g., https://facebook.com/post/123456)',
            'shares': 'Post URL (e.g., https://x.com/user/status/123456)',
            'story_views': 'Story URL (if applicable)',
            'saves': 'Post URL',
            'reach': 'Post or profile URL',
            'engagement': 'Post or profile URL'
        };

        const placeholders = {
            'followers': 'https://instagram.com/username',
            'likes': 'https://instagram.com/p/ABC123/',
            'views': 'https://youtube.com/watch?v=ABC123',
            'comments': 'https://facebook.com/post/123456',
            'shares': 'https://x.com/user/status/123456',
            'story_views': 'https://instagram.com/stories/username/123456',
            'saves': 'https://instagram.com/p/ABC123/',
            'reach': 'https://instagram.com/username or post URL',
            'engagement': 'https://instagram.com/username or post URL'
        };

        urlHelpText.textContent = helpTexts[actionType] || 'Target URL for this action';
        targetUrlInput.placeholder = placeholders[actionType] || 'Enter the target URL...';
    }

    onQuickServiceSearch(e) {
        const query = e.target.value.toLowerCase().trim();
        const dropdown = document.getElementById('quickServiceDropdown');
        
        if (!query || this.quickAllServices.length === 0) {
            dropdown.classList.add('hidden');
            return;
        }

        // Filter services by ID or name
        const filteredServices = this.quickAllServices.filter(service => {
            const searchTerms = [
                service.service_id.toString(),
                service.name.toLowerCase(),
                service.display_text.toLowerCase()
            ];
            return searchTerms.some(term => term.includes(query));
        });

        if (filteredServices.length === 0) {
            dropdown.innerHTML = '<div class="p-3 text-gray-500 text-sm">No services found</div>';
        } else {
            dropdown.innerHTML = filteredServices.slice(0, 10).map(service => `
                <div class="p-3 hover:bg-gray-100 cursor-pointer border-b last:border-b-0" 
                     onclick="app.selectQuickService('${service.service_id}')">
                    <div class="font-medium text-sm">ID: ${service.service_id}</div>
                    <div class="text-gray-600 text-xs">${service.name}</div>
                    <div class="text-blue-600 text-xs">$${service.rate}/1k | Min: ${service.min_quantity} | Max: ${service.max_quantity}</div>
                </div>
            `).join('');
        }

        dropdown.classList.remove('hidden');
    }

    showQuickServiceDropdown() {
        if (this.quickAllServices.length > 0) {
            const searchInput = document.getElementById('quickServiceSearch');
            if (searchInput.value.trim()) {
                this.onQuickServiceSearch({ target: searchInput });
            }
        }
    }

    hideQuickServiceDropdown(e) {
        // Delay hiding to allow clicks on dropdown items
        setTimeout(() => {
            document.getElementById('quickServiceDropdown').classList.add('hidden');
        }, 200);
    }

    selectQuickService(serviceId) {
        const service = this.quickAllServices.find(s => s.service_id.toString() === serviceId.toString());
        if (service) {
            const searchInput = document.getElementById('quickServiceSearch');
            const serviceSelect = document.getElementById('quickJapService');
            
            // Update search input display
            searchInput.value = `ID: ${service.service_id} - ${service.name}`;
            
            // Update hidden select
            serviceSelect.value = service.value;
            
            // Hide dropdown
            document.getElementById('quickServiceDropdown').classList.add('hidden');
            
            // Trigger service change event
            this.onQuickServiceChange({ target: serviceSelect });
        }
    }

    onQuickServiceChange(e) {
        const serviceData = e.target.value;
        const detailsDiv = document.getElementById('quickServiceDetails');
        
        if (serviceData) {
            const service = JSON.parse(serviceData);
            detailsDiv.innerHTML = `
                <div class="text-sm">
                    <p><strong>Service:</strong> ${service.name}</p>
                    <p><strong>Rate:</strong> $${service.rate} per 1000</p>
                    <p><strong>Min Quantity:</strong> ${service.min_quantity}</p>
                    <p><strong>Max Quantity:</strong> ${service.max_quantity}</p>
                    ${service.description ? `<p><strong>Description:</strong> ${service.description}</p>` : ''}
                </div>
            `;
            detailsDiv.classList.remove('hidden');
            this.generateQuickDynamicParameters(service);
        } else {
            detailsDiv.classList.add('hidden');
            this.clearQuickDynamicParameters();
        }
    }

    generateQuickDynamicParameters(service) {
        const container = document.getElementById('quickDynamicParameters');
        container.innerHTML = '';

        // Quantity parameter (always present)
        const quantityDiv = document.createElement('div');
        quantityDiv.innerHTML = `
            <label class="block text-sm font-medium text-gray-700 mb-2">Quantity</label>
            <input type="number" id="quick_param_quantity" required 
                   min="${service.min_quantity}" max="${service.max_quantity}" 
                   value="${service.min_quantity}"
                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
            <p class="text-xs text-gray-500 mt-1">Min: ${service.min_quantity}, Max: ${service.max_quantity}</p>
            <p class="text-xs text-blue-600">Estimated cost: $<span id="quickEstimatedCost">0.00</span></p>
        `;
        container.appendChild(quantityDiv);

        // Add cost calculation
        const quantityInput = quantityDiv.querySelector('#quick_param_quantity');
        quantityInput.addEventListener('input', (e) => {
            const quantity = parseInt(e.target.value) || 0;
            const cost = (quantity / 1000) * service.rate;
            document.getElementById('quickEstimatedCost').textContent = cost.toFixed(2);
        });

        // Trigger initial calculation
        quantityInput.dispatchEvent(new Event('input'));

        // Additional parameters based on service type
        if (service.name.toLowerCase().includes('comment')) {
            const commentsDiv = document.createElement('div');
            commentsDiv.innerHTML = `
                <label class="block text-sm font-medium text-gray-700 mb-2">Custom Comments</label>
                <textarea id="quick_param_custom_comments" rows="4" 
                          placeholder="Enter custom comments (one per line)"
                          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"></textarea>
                <p class="text-xs text-gray-500 mt-1">Leave empty for random comments</p>
            `;
            container.appendChild(commentsDiv);
        }

        // Immediate execution warning
        const warningDiv = document.createElement('div');
        warningDiv.innerHTML = `
            <div class="p-3 bg-red-50 rounded-lg text-sm">
                <i class="fas fa-exclamation-triangle text-red-600 mr-2"></i>
                <span class="text-red-800">This action will be executed immediately and cannot be undone!</span>
            </div>
        `;
        container.appendChild(warningDiv);
    }

    clearQuickDynamicParameters() {
        document.getElementById('quickDynamicParameters').innerHTML = '';
    }

    async handleQuickExecuteSubmit(e) {
        e.preventDefault();
        
        // Get submit button and disable it
        const submitButton = e.target.querySelector('button[type="submit"]');
        const originalText = submitButton.innerHTML;
        
        const serviceData = document.getElementById('quickJapService').value;
        const searchInput = document.getElementById('quickServiceSearch').value;
        const targetUrl = document.getElementById('quickTargetUrl').value;
        
        if (!serviceData || !searchInput.trim()) {
            this.showNotification('Please select a service using the search box', 'error');
            return;
        }

        if (!targetUrl.trim()) {
            this.showNotification('Please enter a target URL', 'error');
            return;
        }

        // Disable button and show loading state
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Executing...';
        submitButton.classList.add('opacity-75', 'cursor-not-allowed');

        const service = JSON.parse(serviceData);
        const parameters = {
            quantity: parseInt(document.getElementById('quick_param_quantity').value),
        };

        // Add optional parameters
        const customComments = document.getElementById('quick_param_custom_comments');
        if (customComments && customComments.value.trim()) {
            parameters.custom_comments = customComments.value.trim();
        }

        try {
            const platform = document.getElementById('quickPlatform').value;
            
            const orderResponse = await fetch(`/api/actions/quick-execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    service_id: service.service_id,
                    service_name: service.name,
                    service_rate: service.rate,
                    platform: platform,
                    link: targetUrl,
                    quantity: parameters.quantity,
                    custom_comments: parameters.custom_comments
                })
            });

            if (orderResponse.ok) {
                const result = await orderResponse.json();
                this.showNotification(`Quick action executed! Order ID: ${result.order_id}`, 'success');
                this.closeQuickExecuteModal();
                
                // Refresh balance
                await this.loadJAPBalance();
            } else {
                const error = await orderResponse.json();
                this.showNotification(error.error || 'Error executing quick action', 'error');
            }
        } catch (error) {
            console.error('Error executing quick action:', error);
            this.showNotification('Error executing quick action', 'error');
        } finally {
            // Re-enable button and restore original text
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
            submitButton.classList.remove('opacity-75', 'cursor-not-allowed');
        }
    }

    // Tab Management
    switchTab(tabName) {
        // Update tab buttons
        document.getElementById('accountsTab').className = tabName === 'accounts' 
            ? 'px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600'
            : 'px-4 py-2 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-700';
        
        document.getElementById('historyTab').className = tabName === 'history'
            ? 'px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600' 
            : 'px-4 py-2 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-700';
        
        // Show/hide content
        document.getElementById('accountsContent').className = tabName === 'accounts' ? '' : 'hidden';
        document.getElementById('historyContent').className = tabName === 'history' ? '' : 'hidden';
        
        // Update button visibility
        document.getElementById('addBtn').style.display = tabName === 'accounts' ? 'flex' : 'none';
        
        this.currentTab = tabName;
        
        if (tabName === 'history') {
            this.loadHistory();
            this.loadHistoryStats();
        }
    }

    // History Management
    async loadHistory() {
        try {
            const filters = this.getHistoryFilters();
            const params = new URLSearchParams({
                limit: this.historyData.limit,
                offset: this.historyData.offset,
                ...filters
            });

            const response = await fetch(`/api/history?${params}`);
            const data = await response.json();
            
            if (data.error) {
                this.showNotification(`Error loading history: ${data.error}`, 'error');
                return;
            }

            this.historyData = data;
            this.renderHistoryTable();
            this.updateHistoryPagination();
        } catch (error) {
            console.error('Error loading history:', error);
            this.showNotification('Error loading history', 'error');
        }
    }

    getHistoryFilters() {
        const filters = {};
        
        const executionType = document.getElementById('filterExecutionType').value;
        const platform = document.getElementById('filterPlatform').value;
        const status = document.getElementById('filterStatus').value;
        
        if (executionType) filters.execution_type = executionType;
        if (platform) filters.platform = platform;
        if (status) filters.status = status;
        
        return filters;
    }

    renderHistoryTable() {
        const tbody = document.getElementById('historyTable');
        const emptyState = document.getElementById('emptyHistoryState');
        
        if (this.historyData.executions.length === 0) {
            tbody.innerHTML = '';
            emptyState.classList.remove('hidden');
            return;
        }
        
        emptyState.classList.add('hidden');
        
        tbody.innerHTML = this.historyData.executions.map(execution => `
            <tr class="hover:bg-gray-50">
                <td class="px-3 py-2 font-mono text-xs">${execution.jap_order_id}</td>
                <td class="px-3 py-2">
                    <span class="inline-flex items-center px-2 py-1 text-xs rounded-full ${
                        execution.execution_type === 'instant' 
                            ? 'bg-orange-100 text-orange-800' 
                            : 'bg-purple-100 text-purple-800'
                    }">
                        <i class="fas ${execution.execution_type === 'instant' ? 'fa-bolt' : 'fa-rss'} mr-1"></i>
                        ${execution.execution_type === 'instant' ? 'Instant' : 'RSS Trigger'}
                    </span>
                </td>
                <td class="px-3 py-2">
                    <div class="flex items-center gap-2">
                        <i class="${this.getPlatformIcon(execution.platform)} text-sm"></i>
                        <span>${execution.platform}</span>
                    </div>
                </td>
                <td class="px-3 py-2 text-sm">${execution.account_username || '-'}</td>
                <td class="px-3 py-2 text-sm" title="${execution.service_name}">
                    ${execution.service_name.length > 25 ? execution.service_name.substring(0, 25) + '...' : execution.service_name}
                </td>
                <td class="px-3 py-2 text-sm">
                    <a href="${execution.target_url}" target="_blank" class="text-blue-500 hover:text-blue-700" title="${execution.target_url}">
                        ${execution.target_url.length > 30 ? execution.target_url.substring(0, 30) + '...' : execution.target_url}
                    </a>
                </td>
                <td class="px-3 py-2 text-sm">${execution.quantity.toLocaleString()}</td>
                <td class="px-3 py-2">
                    <span class="inline-flex items-center px-2 py-1 text-xs rounded-full ${this.getStatusColor(execution.status)}">
                        ${this.formatStatus(execution.status)}
                    </span>
                </td>
                <td class="px-3 py-2 text-sm">${this.formatDate(execution.created_at)}</td>
                <td class="px-3 py-2">
                    <button onclick="app.refreshExecutionStatus('${execution.jap_order_id}')" 
                            class="text-blue-500 hover:text-blue-700 p-1" title="Refresh Status">
                        <i class="fas fa-sync"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    getStatusColor(status) {
        const colors = {
            'pending': 'bg-yellow-100 text-yellow-800',
            'in_progress': 'bg-blue-100 text-blue-800',
            'completed': 'bg-green-100 text-green-800',
            'partial': 'bg-orange-100 text-orange-800',
            'canceled': 'bg-red-100 text-red-800'
        };
        return colors[status] || 'bg-gray-100 text-gray-800';
    }

    formatStatus(status) {
        return status.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleString();
    }

    updateHistoryPagination() {
        const start = this.historyData.offset + 1;
        const end = Math.min(this.historyData.offset + this.historyData.executions.length, this.historyData.total);
        
        document.getElementById('historyStart').textContent = start;
        document.getElementById('historyEnd').textContent = end;
        document.getElementById('historyTotal').textContent = this.historyData.total;
        
        document.getElementById('historyPrevBtn').disabled = this.historyData.offset === 0;
        document.getElementById('historyNextBtn').disabled = end >= this.historyData.total;
    }

    historyPrevPage() {
        if (this.historyData.offset > 0) {
            this.historyData.offset = Math.max(0, this.historyData.offset - this.historyData.limit);
            this.loadHistory();
        }
    }

    historyNextPage() {
        if (this.historyData.offset + this.historyData.limit < this.historyData.total) {
            this.historyData.offset += this.historyData.limit;
            this.loadHistory();
        }
    }

    async loadHistoryStats() {
        try {
            const response = await fetch('/api/history/stats');
            const stats = await response.json();
            
            if (stats.error) {
                console.error('Error loading stats:', stats.error);
                return;
            }

            this.renderHistoryStats(stats);
        } catch (error) {
            console.error('Error loading history stats:', error);
        }
    }

    renderHistoryStats(stats) {
        const container = document.getElementById('historyStats');
        container.innerHTML = `
            <div class="bg-white p-4 rounded-lg border">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-600">Total Executions</p>
                        <p class="text-2xl font-bold text-gray-900">${stats.overall.total_executions || 0}</p>
                    </div>
                    <i class="fas fa-chart-line text-blue-500 text-xl"></i>
                </div>
            </div>
            <div class="bg-white p-4 rounded-lg border">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-600">Completed</p>
                        <p class="text-2xl font-bold text-green-600">${stats.overall.completed || 0}</p>
                    </div>
                    <i class="fas fa-check-circle text-green-500 text-xl"></i>
                </div>
            </div>
            <div class="bg-white p-4 rounded-lg border">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-600">Instant / RSS</p>
                        <p class="text-2xl font-bold text-gray-900">${stats.overall.instant_executions || 0} / ${stats.overall.rss_executions || 0}</p>
                    </div>
                    <i class="fas fa-bolt text-orange-500 text-xl"></i>
                </div>
            </div>
            <div class="bg-white p-4 rounded-lg border">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-600">Total Cost</p>
                        <p class="text-2xl font-bold text-gray-900">$${(stats.overall.total_cost || 0).toFixed(2)}</p>
                    </div>
                    <i class="fas fa-dollar-sign text-green-500 text-xl"></i>
                </div>
            </div>
        `;
    }

    async refreshExecutionStatus(orderId) {
        try {
            const response = await fetch(`/api/history/${orderId}/refresh-status`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.showNotification('Status refreshed successfully', 'success');
                this.loadHistory(); // Reload to show updated status
            } else {
                const error = await response.json();
                this.showNotification(error.error || 'Error refreshing status', 'error');
            }
        } catch (error) {
            console.error('Error refreshing status:', error);
            this.showNotification('Error refreshing status', 'error');
        }
    }

    // Original account methods
    editAccount(id) {
        const account = this.accounts.find(acc => acc.id === id);
        if (account) {
            this.openModal(account);
        }
    }

    async deleteAccount(id) {
        if (!confirm('Are you sure you want to delete this account and all its actions?')) return;

        try {
            const response = await fetch(`/api/accounts/${id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.loadAccounts();
                this.showNotification('Account deleted successfully!', 'success');
            } else {
                this.showNotification('Error deleting account', 'error');
            }
        } catch (error) {
            console.error('Error deleting account:', error);
            this.showNotification('An error occurred while deleting the account', 'error');
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 px-6 py-3 rounded-lg text-white z-50 ${
            type === 'success' ? 'bg-green-500' : 
            type === 'error' ? 'bg-red-500' : 'bg-blue-500'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    // RSS Management Methods
    async refreshRSSStatus(accountId) {
        try {
            const response = await fetch(`/api/accounts/${accountId}/rss-status`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showNotification(`RSS status updated: ${result.message}`, 'success');
                await this.loadAccounts(); // Reload to show updated status
            } else {
                this.showNotification(`Failed to refresh RSS status: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error refreshing RSS status:', error);
            this.showNotification('An error occurred while refreshing RSS status', 'error');
        }
    }

    async retryRSSFeed(accountId) {
        try {
            const response = await fetch(`/api/accounts/${accountId}/rss-feed`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showNotification(`RSS feed created successfully: ${result.message}`, 'success');
                await this.loadAccounts(); // Reload to show updated status
            } else {
                this.showNotification(`Failed to create RSS feed: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error creating RSS feed:', error);
            this.showNotification('An error occurred while creating RSS feed', 'error');
        }
    }
}

// Initialize the app
const app = new SocialMediaManager();