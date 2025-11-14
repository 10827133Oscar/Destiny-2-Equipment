/**
 * Destiny 2 裝備系統 - 前端主程序
 * 
 * 功能模塊：
 * - 添加裝備
 * - 配置套裝
 * - 查看倉庫
 */

// API 基礎 URL
const API_BASE = '';

// 全局數據
let classes = [];
let equipmentTypes = [];
let equipmentTags = [];
let attributes = [];
let currentBuildResult = null;  // 當前搜索結果
let currentBuildConfig = null;  // 當前搜索配置

// 工具函數：防抖
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 工具函數：節流
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// 工具函數：安全的 API 請求
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${url}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
            throw new Error(error.error || `請求失敗: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new Error('無法連接到服務器，請確認服務器正在運行');
        }
        throw error;
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await loadInitialData();
        setupEventListeners();
        setupTabs();
    } catch (error) {
        showError('初始化失敗: ' + error.message);
    }
});

// 載入初始數據
async function loadInitialData() {
    try {
        const [classesData, typesData, tagsData, attrsData] = await Promise.all([
            apiRequest('/api/classes'),
            apiRequest('/api/equipment-types'),
            apiRequest('/api/equipment-tags'),
            apiRequest('/api/attributes')
        ]);

        classes = classesData;
        equipmentTypes = typesData;
        equipmentTags = tagsData;
        attributes = attrsData;

        populateSelects();
        setupAttributeInputs();
    } catch (error) {
        showError('載入數據失敗: ' + error.message);
        throw error;
    }
}

// 填充選擇框
function populateSelects() {
    // 職業選擇
    const classSelects = ['add-class', 'build-class', 'inventory-class', 'builds-class'];
    classSelects.forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            classes.forEach(c => {
                const option = document.createElement('option');
                option.value = c.value;
                option.textContent = c.name;
                select.appendChild(option);
            });
        }
    });

    // 裝備類型
    const typeSelects = ['add-type', 'exotic-type'];
    typeSelects.forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            equipmentTypes.forEach(type => {
                const option = document.createElement('option');
                option.value = type;
                option.textContent = type;
                select.appendChild(option);
            });
        }
    });

    // 裝備標籤
    const tagSelects = ['add-tag', 'exotic-tag'];
    tagSelects.forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            equipmentTags.forEach(tag => {
                const option = document.createElement('option');
                option.value = tag.tag;
                option.textContent = `${tag.tag} (主: ${tag.main_attr}, 副: ${tag.sub_attr})`;
                option.dataset.mainAttr = tag.main_attr;
                option.dataset.subAttr = tag.sub_attr;
                select.appendChild(option);
            });
        }
    });

    // 屬性選擇
    const attrSelects = ['add-locked-attr', 'preferred-attr'];
    attrSelects.forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            attributes.forEach(attr => {
                const option = document.createElement('option');
                option.value = attr;
                option.textContent = attr;
                select.appendChild(option);
            });
        }
    });
}

// 設置屬性輸入框
function setupAttributeInputs() {
    // 目標屬性
    const targetContainer = document.getElementById('target-attributes');
    attributes.forEach(attr => {
        const div = document.createElement('div');
        div.className = 'attribute-input';
        div.innerHTML = `
            <label>${attr}</label>
            <input type="number" name="target_${attr}" min="0" step="1" placeholder="留空跳過">
        `;
        targetContainer.appendChild(div);
    });

    // 異域裝備屬性
    const exoticContainer = document.getElementById('exotic-attributes');
    attributes.forEach(attr => {
        const div = document.createElement('div');
        div.className = 'attribute-input';
        div.innerHTML = `
            <label>${attr}</label>
            <input type="number" name="exotic_${attr}" min="0" step="1" placeholder="留空則為5">
        `;
        exoticContainer.appendChild(div);
    });
}

// 設置事件監聽器
function setupEventListeners() {
    // 添加裝備表單
    document.getElementById('add-equipment-form').addEventListener('submit', handleAddEquipment);
    
    // 標籤選擇變化
    document.getElementById('add-tag').addEventListener('change', updateRandomStatOptions);
    
    // 鎖定屬性複選框
    document.getElementById('add-lock-check').addEventListener('change', (e) => {
        document.getElementById('add-locked-attr').disabled = !e.target.checked;
    });

    // 配置套裝表單
    document.getElementById('build-form').addEventListener('submit', handleConfigureBuild);
    
    // 異域裝備複選框
    document.getElementById('use-exotic-check').addEventListener('change', (e) => {
        document.getElementById('exotic-config').style.display = e.target.checked ? 'block' : 'none';
    });

    // 儲存套裝按鈕
    document.getElementById('save-build-btn').addEventListener('click', handleSaveBuild);

    // 刷新套裝列表
    document.getElementById('refresh-builds').addEventListener('click', loadBuilds);
    
    // 套裝職業選擇
    document.getElementById('builds-class').addEventListener('change', loadBuilds);

    // 刷新倉庫
    document.getElementById('refresh-inventory').addEventListener('click', loadInventory);
    
    // 倉庫職業選擇
    document.getElementById('inventory-class').addEventListener('change', loadInventory);
    
    // 使用事件委託處理刪除按鈕點擊
    document.getElementById('inventory-content').addEventListener('click', async (e) => {
        if (e.target.classList.contains('btn-delete')) {
            const equipmentId = e.target.dataset.equipmentId;
            const className = e.target.dataset.class;
            
            showConfirm(`確定要刪除裝備 ${equipmentId} 嗎？`, async () => {
                await deleteEquipment(equipmentId, className);
            });
        }
    });
}

// 設置標籤切換
function setupTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            // 更新按鈕狀態
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // 更新面板顯示
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.getElementById(`${tab}-panel`).classList.add('active');
            
            // 如果是倉庫標籤，自動載入
            if (tab === 'inventory') {
                loadInventory();
            }
            
            // 如果是我的套裝標籤，自動載入
            if (tab === 'my-builds') {
                loadBuilds();
            }
        });
    });
}

// 更新隨機詞條選項
function updateRandomStatOptions() {
    const tagSelect = document.getElementById('add-tag');
    const randomStatSelect = document.getElementById('add-random-stat');
    const tagInfo = document.getElementById('tag-info');
    
    const selectedOption = tagSelect.options[tagSelect.selectedIndex];
    if (!selectedOption.value) {
        randomStatSelect.innerHTML = '<option value="">請選擇隨機詞條</option>';
        tagInfo.textContent = '';
        return;
    }
    
    const mainAttr = selectedOption.dataset.mainAttr;
    const subAttr = selectedOption.dataset.subAttr;
    
    tagInfo.textContent = `主詞條: ${mainAttr}, 副詞條: ${subAttr}`;
    
    // 過濾掉主詞條和副詞條
    randomStatSelect.innerHTML = '<option value="">請選擇隨機詞條</option>';
    attributes.forEach(attr => {
        if (attr !== mainAttr && attr !== subAttr) {
            const option = document.createElement('option');
            option.value = attr;
            option.textContent = attr;
            randomStatSelect.appendChild(option);
        }
    });
}

// 處理添加裝備
async function handleAddEquipment(e) {
    e.preventDefault();
    const form = e.target;
    const resultBox = document.getElementById('add-result');
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // 禁用提交按鈕防止重複提交
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = '添加中...';
    
    try {
        const data = {
            guardian_class: document.getElementById('add-class').value,
            equipment_type: document.getElementById('add-type').value,
            tag: document.getElementById('add-tag').value,
            random_stat: document.getElementById('add-random-stat').value,
            locked_attr: document.getElementById('add-lock-check').checked 
                ? document.getElementById('add-locked-attr').value 
                : null,
            set_name: document.getElementById('add-set-name').value.trim() || null
        };
        
        // 前端驗證
        if (!data.guardian_class || !data.equipment_type || !data.tag || !data.random_stat) {
            throw new Error('請填寫所有必需字段');
        }
        
        const result = await apiRequest('/api/equipment/add', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            resultBox.className = 'result-box active success';
            resultBox.innerHTML = `
                <h3>✓ 成功添加裝備</h3>
                <p><strong>名稱:</strong> ${escapeHtml(result.equipment.name)}</p>
                <p><strong>ID:</strong> ${escapeHtml(result.equipment.id)}</p>
                <p><strong>類型:</strong> ${escapeHtml(result.equipment.type)}</p>
                <p><strong>屬性:</strong> ${formatAttributes(result.equipment.attributes)}</p>
                ${result.equipment.locked_attr ? `<p><strong>鎖定屬性:</strong> ${escapeHtml(result.equipment.locked_attr)} (+5)</p>` : ''}
            `;
            showSuccess('裝備已成功添加');
            
            // 保存職業和裝備類型的選擇
            const savedClass = document.getElementById('add-class').value;
            const savedType = document.getElementById('add-type').value;
            
            // 重置表單
            form.reset();
            
            // 恢復職業和裝備類型的選擇
            document.getElementById('add-class').value = savedClass;
            document.getElementById('add-type').value = savedType;
            
            // 重置鎖定屬性複選框狀態
            document.getElementById('add-lock-check').checked = false;
            document.getElementById('add-locked-attr').disabled = true;
            
            // 更新隨機詞條選項（因為標籤可能已改變）
            updateRandomStatOptions();
        } else {
            throw new Error(result.error || '添加失敗');
        }
    } catch (error) {
        resultBox.className = 'result-box active error';
        resultBox.innerHTML = `<h3>✗ 添加失敗</h3><p>${escapeHtml(error.message)}</p>`;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

// 處理配置套裝
async function handleConfigureBuild(e) {
    e.preventDefault();
    const form = e.target;
    const resultBox = document.getElementById('build-result');
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // 禁用提交按鈕
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = '搜索中...';
    resultBox.className = 'result-box active';
    resultBox.innerHTML = '<p>正在搜索裝備組合...</p>';
    
    try {
        // 收集目標屬性
        const targetAttributes = {};
        attributes.forEach(attr => {
            const input = document.querySelector(`input[name="target_${attr}"]`);
            const value = parseFloat(input.value);
            if (!isNaN(value) && value > 0) {
                targetAttributes[attr] = value;
            }
        });
        
        if (Object.keys(targetAttributes).length === 0) {
            throw new Error('請至少輸入一個目標屬性');
        }
        
        const data = {
            guardian_class: document.getElementById('build-class').value,
            target_attributes: targetAttributes,
            preferred_attr: document.getElementById('preferred-attr').value || null,
            use_exotic: document.getElementById('use-exotic-check').checked
        };
        
        if (!data.guardian_class) {
            throw new Error('請選擇職業');
        }
        
        // 如果有異域裝備
        if (data.use_exotic) {
            const exoticAttributes = {};
            attributes.forEach(attr => {
                const input = document.querySelector(`input[name="exotic_${attr}"]`);
                const value = parseFloat(input.value);
                // 如果未填或為0，則使用5作為預設值（滿等補充詞條）
                if (!isNaN(value) && value > 0) {
                    exoticAttributes[attr] = value;
                } else {
                    exoticAttributes[attr] = 5;  // 未填時使用5
                }
            });
            
            // 檢查至少3個非零屬性（現在所有屬性都有值，至少是5）
            const nonZeroCount = Object.values(exoticAttributes).filter(v => v > 0).length;
            if (nonZeroCount < 3) {
                throw new Error('異域裝備必須至少有3個非零屬性');
            }
            
            const exoticType = document.getElementById('exotic-type').value;
            if (!exoticType) {
                throw new Error('請選擇異域裝備類型');
            }
            
            data.exotic_equipment = {
                name: document.getElementById('exotic-name').value.trim() || '異域裝備',
                type: exoticType,
                attributes: exoticAttributes,
                level: 0,  // 異域裝備等級固定為0
                tag: document.getElementById('exotic-tag').value || null
            };
        }
        
        const result = await apiRequest('/api/build/configure', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            resultBox.className = 'result-box active success';
            resultBox.innerHTML = formatBuildResult(result);
            
            // 保存當前搜索結果和配置，用於儲存套裝
            currentBuildResult = result.result;
            currentBuildConfig = {
                guardian_class: data.guardian_class,
                target_attributes: data.target_attributes,
                preferred_attr: data.preferred_attr,
                exotic_equipment: data.exotic_equipment
            };
            
            // 顯示儲存套裝容器
            document.getElementById('save-build-container').style.display = 'block';
            document.getElementById('build-name-input').value = '';
        } else {
            throw new Error(result.error || '配置失敗');
        }
    } catch (error) {
        resultBox.className = 'result-box active error';
        resultBox.innerHTML = `<h3>✗ 配置失敗</h3><p>${escapeHtml(error.message)}</p>`;
        // 隱藏儲存套裝容器
        document.getElementById('save-build-container').style.display = 'none';
        currentBuildResult = null;
        currentBuildConfig = null;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

// 處理儲存套裝
async function handleSaveBuild() {
    if (!currentBuildResult || !currentBuildConfig) {
        showError('請先搜索裝備組合');
        return;
    }
    
    const buildName = document.getElementById('build-name-input').value.trim();
    if (!buildName) {
        showError('請輸入套裝名稱');
        return;
    }
    
    const saveBtn = document.getElementById('save-build-btn');
    const originalText = saveBtn.textContent;
    saveBtn.disabled = true;
    saveBtn.textContent = '儲存中...';
    
    try {
        const data = {
            name: buildName,
            guardian_class: currentBuildConfig.guardian_class,
            target_attributes: currentBuildConfig.target_attributes,
            preferred_attr: currentBuildConfig.preferred_attr,
            exotic_equipment: currentBuildConfig.exotic_equipment,
            result: currentBuildResult
        };
        
        const result = await apiRequest('/api/build/save', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            showSuccess('套裝已成功儲存');
            document.getElementById('build-name-input').value = '';
            // 如果當前在「我的套裝」標籤頁，刷新列表
            const activeTab = document.querySelector('.tab-btn.active');
            if (activeTab && activeTab.dataset.tab === 'my-builds') {
                loadBuilds();
            }
        } else {
            throw new Error(result.error || '儲存失敗');
        }
    } catch (error) {
        showError('儲存套裝失敗: ' + error.message);
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
    }
}

// 載入套裝列表
async function loadBuilds() {
    const container = document.getElementById('builds-content');
    const selectedClass = document.getElementById('builds-class').value;
    
    showLoading(container, '載入中...');
    
    try {
        const url = selectedClass 
            ? `/api/build/list?guardian_class=${encodeURIComponent(selectedClass)}`
            : '/api/build/list';
        
        const result = await apiRequest(url);
        
        if (result.success) {
            container.innerHTML = '';
            
            if (!result.builds || result.builds.length === 0) {
                container.innerHTML = '<p class="empty-message">沒有保存的套裝</p>';
                return;
            }
            
            // 顯示套裝列表
            result.builds.forEach(build => {
                displayBuild(container, build);
            });
        } else {
            throw new Error(result.error || '載入失敗');
        }
    } catch (error) {
        container.innerHTML = `<p class="error">載入失敗: ${escapeHtml(error.message)}</p>`;
    }
}

// 顯示套裝
function displayBuild(container, build) {
    const buildDiv = document.createElement('div');
    buildDiv.className = 'build-item';
    
    // 格式化創建時間
    let createdAt = '';
    if (build.created_at) {
        try {
            const date = new Date(build.created_at);
            createdAt = date.toLocaleString('zh-TW');
        } catch (e) {
            createdAt = build.created_at;
        }
    }
    
    buildDiv.innerHTML = `
        <div class="build-header">
            <h3 class="build-name">${escapeHtml(build.name)}</h3>
            <div class="build-header-right">
                <span class="build-class">${escapeHtml(build.guardian_class)}</span>
                <button class="btn-delete btn-small" data-build-id="${escapeHtml(build.id)}" title="刪除套裝">×</button>
            </div>
        </div>
        <div class="build-info">
            <div class="build-meta">
                ${createdAt ? `<span>創建時間: ${escapeHtml(createdAt)}</span>` : ''}
            </div>
            <div class="build-actions">
                <button class="btn btn-secondary btn-small load-build-btn" data-build-id="${escapeHtml(build.id)}">載入到配置頁面</button>
                <button class="btn btn-secondary btn-small view-build-btn" data-build-id="${escapeHtml(build.id)}">查看詳情</button>
            </div>
        </div>
    `;
    
    container.appendChild(buildDiv);
    
    // 綁定載入按鈕
    buildDiv.querySelector('.load-build-btn').addEventListener('click', () => {
        loadBuildToConfigPage(build);
    });
    
    // 綁定查看詳情按鈕
    buildDiv.querySelector('.view-build-btn').addEventListener('click', () => {
        viewBuildDetails(build);
    });
    
    // 綁定刪除按鈕
    buildDiv.querySelector('.btn-delete').addEventListener('click', () => {
        showConfirm(`確定要刪除套裝 "${escapeHtml(build.name)}" 嗎？`, async () => {
            await deleteBuild(build.id);
        });
    });
}

// 載入套裝到配置頁面
function loadBuildToConfigPage(build) {
    // 切換到配置套裝標籤
    const buildTab = document.querySelector('[data-tab="build"]');
    if (buildTab) {
        buildTab.click();
    }
    
    // 設置職業
    document.getElementById('build-class').value = build.guardian_class;
    
    // 設置目標屬性
    if (build.target_attributes) {
        Object.entries(build.target_attributes).forEach(([attr, value]) => {
            const input = document.querySelector(`input[name="target_${attr}"]`);
            if (input) {
                input.value = value;
            }
        });
    }
    
    // 設置偏好屬性
    if (build.preferred_attr) {
        document.getElementById('preferred-attr').value = build.preferred_attr;
    } else {
        document.getElementById('preferred-attr').value = '';
    }
    
    // 設置異域裝備
    if (build.exotic_equipment) {
        document.getElementById('use-exotic-check').checked = true;
        document.getElementById('exotic-config').style.display = 'block';
        
        // 設置異域裝備類型
        document.getElementById('exotic-type').value = build.exotic_equipment.type;
        
        // 設置異域裝備名稱
        document.getElementById('exotic-name').value = build.exotic_equipment.name || '異域裝備';
        
        // 設置異域裝備屬性
        if (build.exotic_equipment.attributes) {
            Object.entries(build.exotic_equipment.attributes).forEach(([attr, value]) => {
                const input = document.querySelector(`input[name="exotic_${attr}"]`);
                if (input) {
                    input.value = value;
                }
            });
        }
        
        // 設置異域裝備標籤
        if (build.exotic_equipment.tag) {
            document.getElementById('exotic-tag').value = build.exotic_equipment.tag;
        } else {
            document.getElementById('exotic-tag').value = '';
        }
    } else {
        document.getElementById('use-exotic-check').checked = false;
        document.getElementById('exotic-config').style.display = 'none';
    }
    
    showSuccess('套裝配置已載入，請點擊「搜索裝備組合」來搜索');
}

// 查看套裝詳情
function viewBuildDetails(build) {
    // 格式化套裝結果
    if (build.result) {
        const formattedResult = formatBuildResultFromData({
            success: true,
            result: build.result,
            formatted: null
        });
        
        // 顯示在彈出框或新區域
        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'build-details-modal';
        detailsDiv.innerHTML = `
            <div class="modal-overlay" style="display: block;">
                <div class="modal-dialog" style="max-width: 800px;">
                    <div class="modal-content">
                        <h3 class="modal-title">${escapeHtml(build.name)} - 套裝詳情</h3>
                        <div class="build-details-content">
                            <div class="result-box active success" style="margin: 0;">
                                ${formattedResult}
                            </div>
                        </div>
                        <div class="modal-actions">
                            <button class="btn btn-primary modal-close">關閉</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(detailsDiv);
        
        // 關閉按鈕
        detailsDiv.querySelector('.modal-close').addEventListener('click', () => {
            detailsDiv.remove();
        });
        
        // 點擊背景關閉
        detailsDiv.querySelector('.modal-overlay').addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-overlay')) {
                detailsDiv.remove();
            }
        });
    }
}

// 從數據格式化套裝結果（用於顯示已保存的套裝）
function formatBuildResultFromData(data) {
    // 如果有格式化的結果，直接使用
    if (data.formatted) {
        return formatBuildResult(data);
    }
    
    // 否則從 result 數據生成
    const result = data.result;
    if (!result) {
        return '<p>無結果數據</p>';
    }
    
    // 使用現有的格式化函數
    return formatBuildResult({
        success: true,
        result: result,
        formatted: null
    });
}

// 刪除套裝
async function deleteBuild(buildId) {
    try {
        const result = await apiRequest('/api/build/delete', {
            method: 'POST',
            body: JSON.stringify({
                build_id: buildId
            })
        });
        
        if (result.success) {
            showSuccess('套裝已成功刪除');
            // 重新載入套裝列表
            await loadBuilds();
        } else {
            throw new Error(result.error || '刪除失敗');
        }
    } catch (error) {
        showError('刪除套裝失敗: ' + error.message);
    }
}

// 刪除裝備
async function deleteEquipment(equipmentId, className) {
    try {
        const result = await apiRequest('/api/equipment/delete', {
            method: 'POST',
            body: JSON.stringify({
                guardian_class: className,
                equipment_id: equipmentId
            })
        });
        
        if (result.success) {
            showSuccess('裝備已成功刪除');
            // 重新載入倉庫
            await loadInventory();
        } else {
            throw new Error(result.error || '刪除失敗');
        }
    } catch (error) {
        showError('刪除裝備失敗: ' + error.message);
    }
}

// 載入倉庫
async function loadInventory() {
    const container = document.getElementById('inventory-content');
    const selectedClass = document.getElementById('inventory-class').value;
    
    showLoading(container);
    
    try {
        const url = selectedClass 
            ? `/api/equipment/list?guardian_class=${encodeURIComponent(selectedClass)}`
            : '/api/equipment/list';
        
        const result = await apiRequest(url);
        
        if (result.success) {
            container.innerHTML = '';
            
            if (selectedClass) {
                // 顯示單一職業
                displayEquipments(container, selectedClass, result.equipments);
            } else {
                // 顯示所有職業
                Object.keys(result.equipments).forEach(className => {
                    displayEquipments(container, className, result.equipments[className]);
                });
            }
        } else {
            throw new Error(result.error || '載入失敗');
        }
    } catch (error) {
        container.innerHTML = `<p class="error">載入失敗: ${escapeHtml(error.message)}</p>`;
    }
}

// 顯示裝備列表
function displayEquipments(container, className, equipments) {
    const section = document.createElement('div');
    section.className = 'class-section';
    
    const title = document.createElement('h3');
    title.textContent = `【${escapeHtml(className)}】`;
    section.appendChild(title);
    
    if (!Array.isArray(equipments) || equipments.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'empty-message';
        empty.textContent = '倉庫為空';
        section.appendChild(empty);
    } else {
        // 按裝備類型分組
        const equipmentTypes = ['頭盔', '臂鎧', '胸鎧', '護腿', '職業物品'];
        const groupedEquipments = {};
        
        equipmentTypes.forEach(type => {
            groupedEquipments[type] = [];
        });
        
        equipments.forEach(eq => {
            if (groupedEquipments[eq.type]) {
                groupedEquipments[eq.type].push(eq);
            }
        });
        
        // 為每個部位創建可展開的區塊
        equipmentTypes.forEach(type => {
            const typeEquipments = groupedEquipments[type];
            if (typeEquipments.length === 0) {
                return; // 跳過空部位
            }
            
            const typeSection = document.createElement('div');
            typeSection.className = 'equipment-type-section';
            
            const typeHeader = document.createElement('div');
            typeHeader.className = 'equipment-type-header';
            typeHeader.innerHTML = `
                <span class="type-header-icon">▼</span>
                <span class="type-header-title">${escapeHtml(type)}</span>
                <span class="type-header-count">(${typeEquipments.length})</span>
            `;
            typeHeader.addEventListener('click', () => {
                const isExpanded = typeSection.classList.contains('expanded');
                if (isExpanded) {
                    typeSection.classList.remove('expanded');
                    typeHeader.querySelector('.type-header-icon').textContent = '▶';
                } else {
                    typeSection.classList.add('expanded');
                    typeHeader.querySelector('.type-header-icon').textContent = '▼';
                }
            });
            typeSection.appendChild(typeHeader);
            
            const typeContent = document.createElement('div');
            typeContent.className = 'equipment-type-content';
            
            typeEquipments.forEach(eq => {
                const item = document.createElement('div');
                item.className = 'equipment-item';
                
                const header = document.createElement('div');
                header.className = 'equipment-header';
                header.innerHTML = `
                    <span class="equipment-name">${escapeHtml(eq.name)}</span>
                    <div class="equipment-header-right">
                        <span class="equipment-id">ID: ${escapeHtml(eq.id)}</span>
                        <button class="btn-delete" data-equipment-id="${escapeHtml(eq.id)}" data-class="${escapeHtml(className)}" title="刪除裝備">×</button>
                    </div>
                `;
                item.appendChild(header);
                
                const info = document.createElement('div');
                info.className = 'equipment-info';
                const infoParts = [];
                if (eq.tag) infoParts.push(`標籤: ${escapeHtml(eq.tag)}`);
                if (eq.level > 0) infoParts.push(`等級: +${eq.level}`);
                if (eq.locked_attr) infoParts.push(`鎖定: ${escapeHtml(eq.locked_attr)} (+5)`);
                if (eq.penalty_attr) infoParts.push(`懲罰: ${escapeHtml(eq.penalty_attr)} (-5)`);
                if (eq.set_name) infoParts.push(`套裝: ${escapeHtml(eq.set_name)}`);
                info.innerHTML = infoParts.map(p => `<span>${p}</span>`).join('');
                item.appendChild(info);
                
                const attrs = document.createElement('div');
                attrs.className = 'equipment-attributes';
                Object.entries(eq.attributes || {}).forEach(([attr, value]) => {
                    const badge = document.createElement('span');
                    badge.className = 'attribute-badge';
                    badge.innerHTML = `<strong>${escapeHtml(attr)}:</strong> ${value}`;
                    attrs.appendChild(badge);
                });
                item.appendChild(attrs);
                
                typeContent.appendChild(item);
            });
            
            typeSection.appendChild(typeContent);
            section.appendChild(typeSection);
            
            // 默認展開第一個有裝備的部位
            if (!section.querySelector('.equipment-type-section.expanded')) {
                typeSection.classList.add('expanded');
            }
        });
    }
    
    container.appendChild(section);
}

// 工具函數：轉義 HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 工具函數：格式化屬性顯示
function formatAttributes(attributes) {
    if (!attributes || typeof attributes !== 'object') {
        return '無';
    }
    return Object.entries(attributes)
        .map(([key, value]) => `${escapeHtml(key)}: ${value}`)
        .join(', ');
}

// 工具函數：格式化配置裝備結果
function formatBuildResult(result) {
    const html = [];
    
    // 解析格式化文本
    const formatted = result.formatted || '';
    const lines = formatted.split('\n');
    
    let currentSection = null;
    let sectionContent = [];
    
    html.push('<div class="build-result-container">');
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        // 跳過分隔線和空行
        if (line === '' || line.match(/^=+$/)) {
            if (currentSection && sectionContent.length > 0) {
                html.push(renderSection(currentSection, sectionContent));
                sectionContent = [];
                currentSection = null;
            }
            continue;
        }
        
        // 檢測標題
        if (line.match(/^【.*】$/)) {
            if (currentSection && sectionContent.length > 0) {
                html.push(renderSection(currentSection, sectionContent));
                sectionContent = [];
            }
            currentSection = line.replace(/【|】/g, '');
            continue;
        }
        
        // 檢測狀態消息
        if (line.startsWith('✓') || line.startsWith('✗')) {
            if (currentSection && sectionContent.length > 0) {
                html.push(renderSection(currentSection, sectionContent));
                sectionContent = [];
                currentSection = null;
            }
            const isSuccess = line.startsWith('✓');
            const message = line.substring(1).trim();
            html.push(`<div class="build-status ${isSuccess ? 'success' : 'error'}">`);
            html.push(`  <span class="status-icon">${isSuccess ? '✓' : '✗'}</span>`);
            html.push(`  <span class="status-message">${escapeHtml(message)}</span>`);
            html.push(`</div>`);
            continue;
        }
        
        // 收集內容
        if (currentSection) {
            sectionContent.push(line);
        } else if (line) {
            // 沒有明確區塊的內容
            sectionContent.push(line);
            if (!currentSection) {
                currentSection = '其他信息';
            }
        }
    }
    
    // 處理最後一個區塊
    if (currentSection && sectionContent.length > 0) {
        html.push(renderSection(currentSection, sectionContent));
    }
    
    html.push('</div>');
    return html.join('\n');
}

// 渲染區塊
function renderSection(title, content) {
    if (content.length === 0) return '';
    
    const html = [];
    html.push(`<div class="build-section">`);
    // 檢查是否為異域裝備標題（格式：部位-異域裝備）
    const isExoticTitle = title.includes('-異域裝備');
    const titleClass = isExoticTitle ? 'section-title exotic-title' : 'section-title';
    html.push(`  <h3 class="${titleClass}">${escapeHtml(title)}</h3>`);
    html.push(`  <div class="section-content">`);
    
    // 解析內容
    let inEquipment = false;
    let equipmentLines = [];
    let equipmentIndex = 0;
    let equipmentName = null;
    
    // 檢查是否為裝備詳情區塊（標題是裝備部位或【部位-異域裝備】）
    const equipmentTypes = ['頭盔', '臂鎧', '胸鎧', '護腿', '職業物品'];
    const isEquipmentDetail = equipmentTypes.includes(title) || 
                               equipmentTypes.some(type => title === `${type}-異域裝備`);
    
    for (const line of content) {
        // 檢測裝備項目（以數字開頭，如 "1. 裝備名稱"）
        if (line.match(/^\s*\d+\.\s+/)) {
            if (inEquipment && equipmentLines.length > 0) {
                html.push(renderEquipmentItem(equipmentIndex, equipmentLines));
                equipmentLines = [];
            }
            inEquipment = true;
            equipmentIndex++;
            equipmentLines.push(line);
        } else if (inEquipment) {
            equipmentLines.push(line);
        } else if (isEquipmentDetail && !line.includes(':')) {
            const trimmedLine = line.trim();
            // 檢測特殊標記（如【異域裝備】）
            if (trimmedLine.match(/^【.*】$/)) {
                const tagText = trimmedLine.replace(/【|】/g, '');
                html.push(`    <div class="equipment-tag">${escapeHtml(tagText)}</div>`);
            } else if (!equipmentName && trimmedLine) {
                // 第一行非冒號、非標題的行是裝備名稱
                equipmentName = trimmedLine;
                html.push(`    <div class="equipment-name">${escapeHtml(equipmentName)}</div>`);
            } else if (trimmedLine) {
                // 其他非鍵值對的文本
                html.push(`    <div class="info-text">${escapeHtml(trimmedLine)}</div>`);
            }
        } else {
            // 普通內容行
            if (line.includes(':')) {
                const [key, ...valueParts] = line.split(':');
                const value = valueParts.join(':').trim();
                html.push(`    <div class="info-row">`);
                html.push(`      <span class="info-key">${escapeHtml(key.trim())}:</span>`);
                html.push(`      <span class="info-value">${escapeHtml(value)}</span>`);
                html.push(`    </div>`);
            } else if (line.trim()) {
                html.push(`    <div class="info-text">${escapeHtml(line.trim())}</div>`);
            }
        }
    }
    
    // 處理最後一個裝備項目
    if (inEquipment && equipmentLines.length > 0) {
        html.push(renderEquipmentItem(equipmentIndex, equipmentLines));
    }
    
    html.push(`  </div>`);
    html.push(`</div>`);
    return html.join('\n');
}

// 渲染裝備項目
function renderEquipmentItem(index, lines) {
    const html = [];
    html.push(`    <div class="equipment-recommendation">`);
    
    // 第一行是標題
    if (lines.length > 0) {
        const titleLine = lines[0].replace(/^\s*\d+\.\s+/, '');
        html.push(`      <h4 class="equipment-title">${escapeHtml(titleLine)}</h4>`);
    }
    
    // 解析其他行
    let currentSubsection = null;
    let subsectionContent = [];
    
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        
        if (line.includes(':')) {
            const [key, ...valueParts] = line.split(':');
            const keyTrimmed = key.trim();
            const value = valueParts.join(':').trim();
            
            // 檢測子區塊標題（如 "滿級屬性:"）
            if (keyTrimmed.endsWith('屬性') || keyTrimmed.endsWith('貢獻') || keyTrimmed === '標籤' || keyTrimmed === '隨機詞條' || keyTrimmed === '鎖定屬性' || keyTrimmed === '總分') {
                if (currentSubsection && subsectionContent.length > 0) {
                    html.push(renderSubsection(currentSubsection, subsectionContent));
                    subsectionContent = [];
                }
                
                if (keyTrimmed === '總分' || keyTrimmed === '標籤' || keyTrimmed === '隨機詞條' || keyTrimmed === '鎖定屬性') {
                    // 單行信息
                    html.push(`        <div class="equipment-info-item">`);
                    html.push(`          <span class="info-key">${escapeHtml(keyTrimmed)}:</span>`);
                    html.push(`          <span class="info-value">${escapeHtml(value)}</span>`);
                    html.push(`        </div>`);
                    currentSubsection = null;
                } else {
                    currentSubsection = keyTrimmed;
                }
            } else if (currentSubsection) {
                subsectionContent.push({ key: keyTrimmed, value: value });
            } else {
                html.push(`        <div class="equipment-info-item">`);
                html.push(`          <span class="info-key">${escapeHtml(keyTrimmed)}:</span>`);
                html.push(`          <span class="info-value">${escapeHtml(value)}</span>`);
                html.push(`        </div>`);
            }
        }
    }
    
    // 處理最後一個子區塊
    if (currentSubsection && subsectionContent.length > 0) {
        html.push(renderSubsection(currentSubsection, subsectionContent));
    }
    
    html.push(`    </div>`);
    return html.join('\n');
}

// 渲染子區塊（如屬性列表）
function renderSubsection(title, items) {
    const html = [];
    html.push(`        <div class="equipment-subsection">`);
    html.push(`          <div class="subsection-title">${escapeHtml(title)}:</div>`);
    html.push(`          <div class="subsection-items">`);
    
    for (const item of items) {
        html.push(`            <div class="subsection-item">`);
        html.push(`              <span class="item-key">${escapeHtml(item.key)}:</span>`);
        html.push(`              <span class="item-value">${escapeHtml(item.value)}</span>`);
        html.push(`            </div>`);
    }
    
    html.push(`          </div>`);
    html.push(`        </div>`);
    return html.join('\n');
}

// 顯示通知消息
function showNotification(message, type = 'error', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span class="notification-icon">${type === 'error' ? '✗' : type === 'success' ? '✓' : 'ℹ'}</span>
        <span class="notification-message">${escapeHtml(message)}</span>
        <button class="notification-close">×</button>
    `;
    
    document.body.appendChild(notification);
    
    // 顯示動畫
    setTimeout(() => notification.classList.add('show'), 10);
    
    // 關閉按鈕
    notification.querySelector('.notification-close').addEventListener('click', () => {
        closeNotification(notification);
    });
    
    // 自動關閉
    if (duration > 0) {
        setTimeout(() => closeNotification(notification), duration);
    }
    
    return notification;
}

// 關閉通知
function closeNotification(notification) {
    notification.classList.remove('show');
    setTimeout(() => notification.remove(), 300);
}

// 顯示錯誤（向後兼容）
function showError(message) {
    showNotification(message, 'error');
}

// 顯示成功消息
function showSuccess(message) {
    showNotification(message, 'success');
}

// 顯示加載狀態
function showLoading(element, text = '載入中...') {
    if (element) {
        element.innerHTML = `<div class="loading-spinner">${escapeHtml(text)}</div>`;
    }
}

// 自定義確認對話框
function showConfirm(message, onConfirm, onCancel = null) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    
    const dialog = document.createElement('div');
    dialog.className = 'modal-dialog';
    dialog.innerHTML = `
        <div class="modal-content">
            <h3 class="modal-title">確認</h3>
            <p class="modal-message">${escapeHtml(message)}</p>
            <div class="modal-actions">
                <button class="btn btn-secondary modal-cancel">取消</button>
                <button class="btn btn-primary modal-confirm">確認</button>
            </div>
        </div>
    `;
    
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
    
    // 顯示動畫
    setTimeout(() => overlay.classList.add('show'), 10);
    
    // 確認按鈕
    dialog.querySelector('.modal-confirm').addEventListener('click', () => {
        overlay.classList.remove('show');
        setTimeout(() => overlay.remove(), 300);
        if (onConfirm) onConfirm();
    });
    
    // 取消按鈕
    dialog.querySelector('.modal-cancel').addEventListener('click', () => {
        overlay.classList.remove('show');
        setTimeout(() => overlay.remove(), 300);
        if (onCancel) onCancel();
    });
    
    // 點擊背景關閉
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.classList.remove('show');
            setTimeout(() => overlay.remove(), 300);
            if (onCancel) onCancel();
        }
    });
}

