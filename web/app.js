// ==================== TypeOwl Web App ====================
class TypeOwlApp {
    constructor() {
        this.tg = window.Telegram?.WebApp;
        this.apiBase = '/api';
        this.userId = this.getUserId();
        this.selectedLangs = new Set(['ru']);
        this.currentScreen = 'loading';
        this.sessionId = null;
        this.lessonData = null;
        this.currentCharIndex = 0;
        this.errors = new Set();
        this.hearts = 5;
        this.xpEarned = 0;
        this.correctChars = 0;
        this.charsTyped = 0;
        this.startTime = 0;
        this.perfectStreak = 0;

        this.screens = {
            loading: document.getElementById('loading'),
            menu: document.getElementById('menu'),
            lesson: document.getElementById('lesson'),
            profile: document.getElementById('profile'),
            settings: document.getElementById('settings')
        };

        this.init();
    }

    getUserId() {
        let id = localStorage.getItem('typeowl_user_id');
        if (!id) {
            id = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('typeowl_user_id', id);
        }
        return parseInt(id.replace(/\D/g, '')) || 1;
    }

    init() {
        this.initTelegramWebApp();
        this.bindEvents();
        this.loadUserData();
    }

    initTelegramWebApp() {
        if (this.tg) {
            this.tg.expand();
            this.tg.setHeaderColor('#58CC02');
            this.tg.setBackgroundColor('#F7F7F7');
            this.tg.ready();

            this.tg.BackButton.onClick(() => this.handleBack());
            this.tg.MainButton.setParams({ color: '#58CC02', text_color: '#ffffff' });

            // Haptic feedback on clicks
            document.addEventListener('click', (e) => {
                const btn = e.target.closest('.btn-primary, .btn-secondary, .btn-ghost, .btn-danger, .nav-btn, .lang-btn, .key, .modal button');
                if (btn && this.tg.HapticFeedback) {
                    this.tg.HapticFeedback.impactOccurred('light');
                }
            });

            // Theme handling
            this.tg.onEvent('themeChanged', () => this.applyTheme());
            this.applyTheme();

            console.log('Telegram Web App initialized');
        }
    }

    applyTheme() {
        if (!this.tg) return;
        const isDark = this.tg.colorScheme === 'dark';
        document.documentElement.style.setProperty('--bg', isDark ? '#1A1A2E' : '#F7F7F7');
        document.documentElement.style.setProperty('--bg-card', isDark ? '#232342' : '#FFFFFF');
        document.documentElement.style.setProperty('--bg-input', isDark ? '#2A2A4A' : '#F0F0F0');
        document.documentElement.style.setProperty('--text', isDark ? '#F0F0F0' : '#1A1A2E');
        document.documentElement.style.setProperty('--text-secondary', isDark ? '#A0A0B0' : '#6B6B6B');
        document.documentElement.style.setProperty('--text-muted', isDark ? '#707080' : '#999999');
        document.documentElement.style.setProperty('--border', isDark ? '#3A3A5A' : '#E0E0E0');
        document.documentElement.style.setProperty('--shadow', isDark ? '0 2px 8px rgba(0,0,0,0.3)' : '0 2px 8px rgba(0,0,0,0.06)');
    }

    bindEvents() {
        // Language buttons
        document.querySelectorAll('.lang-btn').forEach(btn => {
            btn.addEventListener('click', () => this.toggleLang(btn.dataset.lang));
        });

        // Start button
        document.getElementById('start-btn').addEventListener('click', () => this.startLesson());

        // Bottom nav
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => this.showScreen(btn.dataset.screen));
        });

        // Lesson controls
        document.getElementById('btn-backspace').addEventListener('click', () => this.handleBackspace());
        document.getElementById('btn-exit').addEventListener('click', () => this.exitLesson());

        // Modal buttons
        document.getElementById('modal-next').addEventListener('click', () => this.nextLesson());
        document.getElementById('modal-retry').addEventListener('click', () => this.retryLesson());
        document.getElementById('modal-menu').addEventListener('click', () => this.goToMenu());
        document.getElementById('modal-backdrop').addEventListener('click', () => this.goToMenu());

        // Keyboard input
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
        document.addEventListener('keydown', (e) => {
            if (this.currentScreen === 'lesson' && [' ', 'ArrowLeft', 'ArrowRight', 'Backspace'].includes(e.key)) {
                e.preventDefault();
            }
        }, { passive: false });

        // Settings lang toggles
        document.addEventListener('change', (e) => {
            if (e.target.matches('.lang-toggle input')) {
                const lang = e.target.closest('.lang-toggle').dataset.lang;
                this.toggleSettingsLang(lang, e.target.checked);
            }
        });
    }

    showScreen(screenName) {
        Object.values(this.screens).forEach(s => s.classList.remove('active'));
        this.screens[screenName].classList.add('active');
        this.currentScreen = screenName;

        // Update nav buttons
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.screen === screenName);
        });

        // Back button visibility
        if (this.tg) {
            this.tg.BackButton[screenName === 'menu' ? 'hide' : 'show']();
        }

        // Load screen-specific data
        if (screenName === 'profile') this.loadProfile();
        if (screenName === 'settings') this.loadSettings();
    }

    handleBack() {
        if (this.currentScreen === 'lesson') {
            this.exitLesson();
        } else if (this.currentScreen !== 'menu') {
            this.showScreen('menu');
        } else if (this.tg) {
            this.tg.close();
        }
    }

    // ==================== API ====================
    async api(endpoint, data = {}) {
        const url = `${this.apiBase}${endpoint}`;
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...data, user_id: this.userId })
        });
        if (!res.ok) throw new Error(`API ${endpoint} failed: ${res.status}`);
        return res.json();
    }

    async loadUserData() {
        try {
            const user = await this.api('/stats', {});
            this.updateMenu(user);
            this.selectedLangs = new Set(user.selected_languages || ['ru']);
            this.updateLangButtons();
            document.getElementById('start-btn').disabled = this.selectedLangs.size === 0;
        } catch (e) {
            console.error('Load user data failed:', e);
        } finally {
            this.showScreen('menu');
        }
    }

    updateMenu(user) {
        document.getElementById('user-greeting').textContent = `Привет, ${user.username || 'друг'}! 🦉`;
        document.getElementById('stat-xp').textContent = (user.xp || 0).toLocaleString();
        document.getElementById('stat-streak').textContent = user.streak || 0;
        document.getElementById('stat-level').textContent = user.level || 1;

        const flags = (user.selected_languages || ['ru']).map(c => ({ ru: '🇷🇺', en: '🇺🇸' })[c] || c).join(' ');
        document.getElementById('user-langs').textContent = flags || 'Выбери язык';

        if (user.lessons_completed > 0) {
            document.getElementById('quick-stats').style.display = 'flex';
            document.getElementById('qs-lessons').textContent = user.lessons_completed;
            document.getElementById('qs-wpm').textContent = Math.round(user.best_wpm || 0);
            document.getElementById('qs-acc').textContent = Math.round(user.best_accuracy || 0) + '%';
        }
    }

    updateLangButtons() {
        document.querySelectorAll('.lang-btn').forEach(btn => {
            const pressed = this.selectedLangs.has(btn.dataset.lang);
            btn.setAttribute('aria-pressed', pressed);
        });
        document.getElementById('start-btn').disabled = this.selectedLangs.size === 0;
    }

    toggleLang(lang) {
        if (this.selectedLangs.has(lang)) {
            if (this.selectedLangs.size === 1) return;
            this.selectedLangs.delete(lang);
        } else {
            this.selectedLangs.add(lang);
        }
        this.updateLangButtons();
    }

    async startLesson() {
        if (this.selectedLangs.size === 0) return;
        const lang = this.selectedLangs.values().next().value; // first selected
        const level = 1; // TODO: get from user level

        try {
            const data = await this.api('/lesson', { language: lang, level });
            this.sessionId = data.session_id;
            this.lessonData = data;
            this.currentCharIndex = 0;
            this.errors = new Set();
            this.hearts = 5;
            this.xpEarned = 0;
            this.correctChars = 0;
            this.charsTyped = 0;
            this.startTime = Date.now();
            this.perfectStreak = 0;

            this.renderLesson();
            this.showScreen('lesson');
        } catch (e) {
            console.error('Start lesson failed:', e);
            alert('Не удалось загрузить урок');
        }
    }

    renderLesson() {
        if (!this.lessonData) return;

        // Render text
        this.renderText();

        // Render keyboard
        this.renderKeyboard();

        // Update stats display
        this.updateLessonStats();

        // Hint
        this.updateHint();
    }

    renderText() {
        const container = document.getElementById('text-line');
        const text = this.lessonData.lesson_text;

        let html = '';
        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            let classes = 'char';

            if (i < this.currentCharIndex) {
                classes += this.errors.has(i) ? ' error' : ' correct';
            } else if (i === this.currentCharIndex) {
                classes += ' current';
            } else {
                classes += ' upcoming';
            }

            const escaped = this.escapeHtml(char);
            html += `<span class="${classes}">${escaped === ' ' ? '␣' : escaped}</span>`;
        }

        container.innerHTML = html;
        this.updateCaret();
    }

    updateCaret() {
        const currentChar = document.querySelector('.char.current');
        const caret = document.getElementById('caret');
        const textArea = document.getElementById('text-area');
        if (currentChar && caret && textArea) {
            const rect = currentChar.getBoundingClientRect();
            const containerRect = textArea.getBoundingClientRect();
            caret.style.left = (rect.left - containerRect.left) + 'px';
            caret.style.top = (rect.top - containerRect.top) + 'px';
            caret.style.height = rect.height + 'px';
        }
    }

    updateHint() {
        const nextChars = this.lessonData.lesson_text.slice(this.currentCharIndex, this.currentCharIndex + 3);
        const nextKey = document.getElementById('next-key');
        const nextText = document.getElementById('next-text');

        if (this.currentCharIndex < this.lessonData.lesson_text.length) {
            const char = this.lessonData.lesson_text[this.currentCharIndex];
            nextKey.textContent = char === ' ' ? 'Space' : char.toUpperCase();
            nextText.textContent = nextChars.slice(1);
        } else {
            nextKey.textContent = '✓';
            nextText.textContent = 'Готово!';
        }
    }

    renderKeyboard() {
        if (!this.lessonData) return;

        const container = document.getElementById('keyboard-wrap');
        const layout = this.lessonData.keyboard_layout;

        let html = '';
        layout.rows.forEach((row, rowIndex) => {
            html += '<div class="keyboard-row">';
            row.forEach((key, keyIndex) => {
                const shiftKey = layout.shift_rows[rowIndex]?.[keyIndex] || key.toUpperCase();
                const finger = layout.finger_map[key.toLowerCase()];
                const fingerName = layout.finger_names[finger] || '';
                const isSpace = key === ' ';

                let keyClass = 'key';
                if (isSpace) keyClass += ' space';
                else if (key.length > 1 || ['[', ']', '\\', ';', '\'', ',', '.', '/'].includes(key)) keyClass += ' wide';

                html += `
                    <button class="${keyClass}" data-key="${this.escapeHtml(key)}" data-finger="${finger}" data-finger-name="${fingerName}" tabindex="-1">
                        <span class="key-main">${isSpace ? 'Space' : this.escapeHtml(key)}</span>
                        <span class="key-shift">${this.escapeHtml(shiftKey)}</span>
                    </button>
                `;
            });
            html += '</div>';
        });

        container.innerHTML = html;

        // Add hover/focus for finger highlight
        container.querySelectorAll('.key').forEach(btn => {
            btn.addEventListener('mouseenter', () => this.highlightFinger(btn.dataset.finger));
            btn.addEventListener('mouseleave', () => this.clearFingerHighlight());
            btn.addEventListener('focus', () => this.highlightFinger(btn.dataset.finger));
            btn.addEventListener('blur', () => this.clearFingerHighlight());
        });
    }

    highlightFinger(fingerId) {
        if (!fingerId) return;
        document.querySelectorAll(`.key[data-finger="${fingerId}"]`).forEach(k => k.classList.add('finger-active'));
        const name = document.querySelector(`.key[data-finger="${fingerId}"]`)?.dataset.fingerName;
        // Could show finger name somewhere
    }

    clearFingerHighlight() {
        document.querySelectorAll('.key.finger-active').forEach(k => k.classList.remove('finger-active'));
    }

    async handleKeydown(e) {
        if (this.currentScreen !== 'lesson') return;

        if (e.key === 'Backspace') {
            e.preventDefault();
            this.handleBackspace();
            return;
        }
        if (e.key === 'Escape') {
            this.exitLesson();
            return;
        }

        // Regular character
        if (e.key.length === 1 || e.key === ' ') {
            e.preventDefault();
            await this.processKeystroke(e.key === ' ' ? ' ' : e.key);
        }
    }

    async processKeystroke(char) {
        if (!this.sessionId || this.currentCharIndex >= this.lessonData.lesson_text.length) return;

        try {
            const res = await this.api('/keystroke', {
                session_id: this.sessionId,
                char: char,
                timestamp: Date.now() / 1000
            });

            // Visual feedback on keyboard
            this.showKeyFeedback(char, res.correct);

            // Highlight finger
            const keyEl = document.querySelector(`.key[data-key="${this.escapeHtml(char)}"]`);
            if (keyEl?.dataset.finger) {
                this.highlightFinger(keyEl.dataset.finger);
                setTimeout(() => this.clearFingerHighlight(), 200);
            }

            if (res.correct) {
                this.currentCharIndex = res.position;
                this.correctChars = res.correct_chars || this.correctChars + 1;
                this.perfectStreak++;
            } else {
                this.errors.add(this.currentCharIndex);
                this.hearts = res.hearts;
                this.perfectStreak = 0;
            }

            this.charsTyped = res.chars_typed || this.charsTyped + 1;
            this.xpEarned = res.xp_earned || this.xpEarned;

            this.renderText();
            this.updateLessonStatsFromResult(res);
            this.updateHint();

            if (res.complete) {
                this.showResult(res);
            } else if (res.failed) {
                this.showFailed(res);
            }
        } catch (e) {
            console.error('Keystroke error:', e);
        }
    }

    showKeyFeedback(char, correct) {
        const keyEl = document.querySelector(`.key[data-key="${this.escapeHtml(char)}"]`);
        if (keyEl) {
            keyEl.classList.add(correct ? 'correct' : 'error');
            setTimeout(() => keyEl.classList.remove('correct', 'error'), 250);
        }
    }

    async handleBackspace() {
        if (!this.sessionId || this.currentCharIndex === 0) return;

        try {
            const res = await this.api('/backspace', { session_id: this.sessionId });
            this.currentCharIndex = res.position;
            if (this.errors.has(this.currentCharIndex)) this.errors.delete(this.currentCharIndex);
            this.hearts = res.hearts;
            this.correctChars = res.correct_chars;
            this.charsTyped = res.chars_typed;
            this.renderText();
            this.updateLessonStatsFromResult({ hearts: res.hearts, progress: Math.round((res.position / this.lessonData.lesson_text.length) * 100) });
            this.updateHint();
        } catch (e) {
            console.error('Backspace error:', e);
        }
    }

    updateLessonStats() {
        document.getElementById('hearts-display').textContent = '❤️'.repeat(this.hearts) + '🤍'.repeat(5 - this.hearts);
        document.getElementById('xp-display').textContent = `+${this.xpEarned} XP`;
        document.getElementById('acc-display').textContent = this.charsTyped > 0 ? `${Math.round(this.correctChars / this.charsTyped * 100)}%` : '100%';
        const pct = this.lessonData ? Math.round((this.currentCharIndex / this.lessonData.lesson_text.length) * 100) : 0;
        document.getElementById('progress-fill').style.width = pct + '%';
        document.getElementById('progress-text').textContent = pct + '%';
    }

    updateLessonStatsFromResult(res) {
        this.hearts = res.hearts ?? this.hearts;
        this.correctChars = res.correct_chars ?? this.correctChars;
        this.charsTyped = res.chars_typed ?? this.charsTyped;
        this.xpEarned = res.xp_earned ?? this.xpEarned;
        this.updateLessonStats();
    }

    showResult(res) {
        const accuracy = res.accuracy ?? (this.charsTyped > 0 ? this.correctChars / this.charsTyped * 100 : 100);
        const wpm = res.wpm ?? 0;

        // Send to Telegram bot
        if (this.tg && this.tg.sendData) {
            this.tg.sendData(JSON.stringify({
                type: 'lesson_complete',
                session_id: this.sessionId,
                level: this.lessonData.level,
                language: this.lessonData.language,
                wpm, accuracy, xp_earned: this.xpEarned,
                hearts_remaining: this.hearts,
                complete: true, failed: false
            }));
        }

        // Modal content
        const stars = accuracy >= 100 ? 3 : accuracy >= 95 ? 3 : accuracy >= 90 ? 2 : 1;
        document.getElementById('modal-emoji').textContent = stars === 3 ? '🏆' : '🎉';
        document.getElementById('modal-title').textContent = stars === 3 ? 'Идеально!' : 'Урок пройден!';
        document.getElementById('modal-subtitle').textContent = stars === 3 ? 'Ты молодец! 🦉' : 'Отличная работа!';

        document.getElementById('modal-stats').innerHTML = `
            <div class="modal-stat"><span class="val">${wpm}</span><span class="lbl">WPM</span></div>
            <div class="modal-stat"><span class="val">${accuracy}%</span><span class="lbl">Точность</span></div>
            <div class="modal-stat"><span class="val">${this.hearts}/5</span><span class="lbl">Сердца</span></div>
        `;

        // XP breakdown
        const baseXp = this.correctChars * 2;
        let xpHtml = `<h3>💎 XP: +${this.xpEarned}</h3>
            <div class="xp-row"><span>✍️ Верных знаков</span><span>+${baseXp}</span></div>`;
        if (accuracy >= 100) xpHtml += `<div class="xp-row bonus"><span>💎 Идеальная точность!</span><span>+20</span></div>`;
        else if (accuracy >= 95) xpHtml += `<div class="xp-row bonus"><span>🎯 Точность ${accuracy}%</span><span>+20</span></div>`;
        else if (accuracy >= 90) xpHtml += `<div class="xp-row bonus"><span>🎯 Точность ${accuracy}%</span><span>+10</span></div>`;
        else if (accuracy >= 80) xpHtml += `<div class="xp-row bonus"><span>🎯 Точность ${accuracy}%</span><span>+5</span></div>`;
        xpHtml += `<div class="xp-row total"><span>Итого</span><span>+${this.xpEarned} XP</span></div>`;
        document.getElementById('xp-breakdown').innerHTML = xpHtml;

        document.getElementById('modal').classList.remove('hidden');
    }

    showFailed(res) {
        if (this.tg && this.tg.sendData) {
            this.tg.sendData(JSON.stringify({
                type: 'lesson_complete', session_id: this.sessionId,
                level: this.lessonData.level, language: this.lessonData.language,
                wpm: res.wpm, accuracy: res.accuracy, xp_earned: this.xpEarned,
                hearts_remaining: 0, complete: false, failed: true
            }));
        }

        document.getElementById('modal-emoji').textContent = '💔';
        document.getElementById('modal-title').textContent = 'Сердца закончились';
        document.getElementById('modal-subtitle').textContent = 'Не расстраивайся, попробуй ещё раз!';

        document.getElementById('modal-stats').innerHTML = `
            <div class="modal-stat"><span class="val">${res.wpm || 0}</span><span class="lbl">WPM</span></div>
            <div class="modal-stat"><span class="val">${res.accuracy || 0}%</span><span class="lbl">Точность</span></div>
        `;

        document.getElementById('xp-breakdown').innerHTML = `
            <h3>💎 XP: +${this.xpEarned}</h3>
            <div class="xp-row"><span>✍️ За верные знаки</span><span>+${this.xpEarned}</span></div>
            <div class="xp-row total"><span>Итого</span><span>+${this.xpEarned} XP</span></div>
        `;

        document.getElementById('modal').classList.remove('hidden');
    }

    async nextLesson() {
        document.getElementById('modal').classList.add('hidden');
        const nextLevel = Math.min(this.lessonData.level + 1, 5);
        const lang = this.lessonData.language;
        try {
            const data = await this.api('/lesson', { language: lang, level: nextLevel });
            this.sessionId = data.session_id;
            this.lessonData = data;
            this.currentCharIndex = 0;
            this.errors = new Set();
            this.hearts = 5;
            this.xpEarned = 0;
            this.correctChars = 0;
            this.charsTyped = 0;
            this.perfectStreak = 0;
            this.renderLesson();
        } catch (e) {
            console.error('Next lesson failed:', e);
        }
    }

    async retryLesson() {
        document.getElementById('modal').classList.add('hidden');
        await this.startLesson();
    }

    goToMenu() {
        document.getElementById('modal').classList.add('hidden');
        this.showScreen('menu');
        this.loadUserData();
    }

    exitLesson() {
        if (confirm('Выйти из урока? Прогресс не сохранится.')) {
            this.goToMenu();
        }
    }

    // ==================== Profile ====================
    async loadProfile() {
        try {
            const user = await this.api('/stats', {});
            const totalXp = user.xp || 0;
            const achievements = this.getAchievements(user);

            document.getElementById('profile-content').innerHTML = `
                <div class="profile-header">
                    <div class="profile-avatar">🦉</div>
                    <h2 class="profile-name">${user.username || 'Игрок'}</h2>
                    <div class="profile-level">Уровень ${user.level}: ${this.getLevelName(user.level)}</div>
                </div>
                <div class="profile-grid">
                    <div class="profile-stat"><div class="icon">💎</div><div class="val">${totalXp.toLocaleString()}</div><div class="lbl">XP</div></div>
                    <div class="profile-stat"><div class="icon">🔥</div><div class="val">${user.streak || 0}</div><div class="lbl">Стрик</div></div>
                    <div class="profile-stat"><div class="icon">📚</div><div class="val">${user.lessons_completed || 0}</div><div class="lbl">Уроков</div></div>
                    <div class="profile-stat"><div class="icon">⚡</div><div class="val">${(user.best_wpm || 0).toFixed(1)}</div><div class="lbl">Лучший WPM</div></div>
                </div>
                <h3 class="section-title">🏅 Достижения</h3>
                <div class="achievement-list">
                    ${achievements.map(a => `
                        <div class="achievement-item">
                            <span class="achievement-icon">${a.icon}</span>
                            <div class="achievement-text">
                                <div class="achievement-name">${a.name}</div>
                                <div class="achievement-desc">${a.desc}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <h3 class="section-title">📝 Последние уроки</h3>
                <div class="lesson-list">
                    ${(user.recent_lessons || []).slice(0, 10).map(l => `
                        <div class="lesson-item">
                            <span class="lesson-flag">${{ ru: '🇷🇺', en: '🇺🇸' }[l.language] || '🌐'}</span>
                            <div class="lesson-info">
                                <div class="lesson-lang">${{ ru: 'Русский', en: 'English' }[l.language] || l.language} • Ур. ${l.level}</div>
                                <div class="lesson-details">${l.created_at?.slice(0, 10) || 'Недавно'}</div>
                            </div>
                            <div class="lesson-stats-mini">
                                <span>${(l.wpm || 0).toFixed(0)} WPM</span>
                                <span>${(l.accuracy || 0).toFixed(0)}%</span>
                            </div>
                        </div>
                    `).join('') || '<p style="text-align:center;color:var(--text-secondary);padding:20px;">Уроков пока нет</p>'}
                </div>
            `;
        } catch (e) {
            console.error('Load profile failed:', e);
        }
    }

    getLevelName(level) {
        const names = { 1: 'Новичок', 2: 'Начинающий', 3: 'Любитель', 4: 'Профи', 5: 'Мастер' };
        return names[level] || 'Новичок';
    }

    getAchievements(user) {
        const list = [];
        if (user.lessons_completed >= 1) list.push({ icon: '🥇', name: 'Первый шаг', desc: 'Пройди первый урок' });
        if (user.lessons_completed >= 10) list.push({ icon: '🥈', name: 'Наставник', desc: 'Пройди 10 уроков' });
        if (user.lessons_completed >= 50) list.push({ icon: '🥉', name: 'Мастер', desc: 'Пройди 50 уроков' });
        if (user.lessons_completed >= 100) list.push({ icon: '🏆', name: 'Легенда', desc: 'Пройди 100 уроков!' });
        if (user.best_wpm >= 40) list.push({ icon: '⚡', name: 'Скорость света', desc: 'Достигни 40 WPM' });
        if (user.best_wpm >= 60) list.push({ icon: '🚀', name: 'Космическая скорость', desc: 'Достигни 60 WPM' });
        if (user.best_accuracy >= 95) list.push({ icon: '🎯', name: 'Снайпер', desc: 'Точность 95%+' });
        if (user.streak >= 7) list.push({ icon: '🔥', name: 'Неделя подряд', desc: 'Занимайся 7 дней подряд' });
        if (user.streak >= 30) list.push({ icon: '💎', name: 'Железная воля', desc: '30 дней подряд!' });
        return list;
    }

    // ==================== Settings ====================
    async loadSettings() {
        try {
            const user = await this.api('/stats', {});
            const savedLangs = user.selected_languages || ['ru'];

            document.getElementById('settings-content').innerHTML = `
                <div class="setting-group">
                    <h3>Языки обучения</h3>
                    ${Object.entries({ ru: 'Русский', en: 'English' }).map(([code, name]) => `
                        <label class="lang-toggle" data-lang="${code}">
                            <input type="checkbox" ${savedLangs.includes(code) ? 'checked' : ''}>
                            <span class="checkmark"></span>
                            <span class="lang-flag">${code === 'ru' ? '🇷🇺' : '🇺🇸'}</span>
                            <span class="lang-name">${name}</span>
                        </label>
                    `).join('')}
                </div>
                <div class="setting-group">
                    <h3>О приложении</h3>
                    <div class="info-card">
                        <strong>TypeOwl</strong> — тренажёр слепой печати в стиле Duolingo.<br>
                        Версия 1.0 • Открытый исходный код<br>
                        <a href="https://github.com" target="_blank">GitHub</a>
                    </div>
                </div>
            `;
        } catch (e) {
            console.error('Load settings failed:', e);
        }
    }

    toggleSettingsLang(lang, checked) {
        if (!checked && this.selectedLangs.size === 1 && this.selectedLangs.has(lang)) {
            // Prevent unchecking last language
            document.querySelector(`.lang-toggle[data-lang="${lang}"] input`).checked = true;
            return;
        }

        if (checked) this.selectedLangs.add(lang);
        else this.selectedLangs.delete(lang);

        this.updateLangButtons();

        // Save to server (would need API endpoint)
        // this.api('/settings/lang', { languages: Array.from(this.selectedLangs) });
    }

    // ==================== Utils ====================
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.app = new TypeOwlApp();
});