//* =====================================================================================
//*  Main JavaScript — theme, menu, chat, notification sounds
//* =====================================================================================

document.addEventListener('DOMContentLoaded', function () {

    //* ═══════════════════════════════════════════════════════════════════════════════
    //*  Theme Toggle (light/dark theme)
    //* ═══════════════════════════════════════════════════════════════════════════════

    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;

    //* Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    html.setAttribute('data-theme', savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            const current = html.getAttribute('data-theme');
            const newTheme = current === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    //* ═══════════════════════════════════════════════════════════════════════════════
    //*  Mobile Sidebar
    //* ═══════════════════════════════════════════════════════════════════════════════

    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const sidebarClose = document.getElementById('sidebarClose');

    function openSidebar() {
        if (sidebar) sidebar.classList.add('open');
        if (sidebarOverlay) sidebarOverlay.classList.add('active');
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('open');
        if (sidebarOverlay) sidebarOverlay.classList.remove('active');
    }

    if (menuToggle) menuToggle.addEventListener('click', openSidebar);
    if (sidebarClose) sidebarClose.addEventListener('click', closeSidebar);
    if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

    //* Close sidebar on nav item click (mobile)
    if (sidebar) {
        sidebar.querySelectorAll('.nav-item').forEach(function(item) {
            item.addEventListener('click', function() {
                if (window.innerWidth <= 768) closeSidebar();
            });
        });
    }

    //* ═══════════════════════════════════════════════════════════════════════════════
    //*  Chat — notification sound (Web Audio API) + polling
    //* ═══════════════════════════════════════════════════════════════════════════════

    let lastCheck = new Date().toISOString();
    let audioCtx = null;

    //! Notification sound playback function (like in Telegram/WhatsApp)
    function playNotificationSound() {
        try {
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            //* Pleasant two-tone sound
            osc.frequency.setValueAtTime(800, audioCtx.currentTime);
            osc.frequency.setValueAtTime(1000, audioCtx.currentTime + 0.1);
            osc.type = 'sine';

            gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);

            osc.start(audioCtx.currentTime);
            osc.stop(audioCtx.currentTime + 0.3);
        } catch (e) {
            //* If sound doesn't work — ignore
            console.log('Sound not available');
        }
    }

    //* Check new messages (polling every 5 seconds)
    const chatBadge = document.getElementById('chatBadge');

    function checkNewMessages() {
        fetch('/chat/api/messages/new?after=' + encodeURIComponent(lastCheck))
            .then(r => r.json())
            .then(messages => {
                if (messages.length > 0) {
                    //* Update last check time
                    lastCheck = new Date().toISOString();

                    //* Play sound for each new message
                    if (document.hidden || !document.hasFocus()) {
                        playNotificationSound();
                    }

                    //* Update unread badge
                    updateUnreadCount();
                }
            })
            .catch(() => {});
    }

    function updateUnreadCount() {
        fetch('/chat/api/unread-count')
            .then(r => r.json())
            .then(data => {
                const mobileChatBadge = document.getElementById('mobileChatBadge');
                if (chatBadge) {
                    if (data.unread > 0) {
                        chatBadge.style.display = 'inline';
                        chatBadge.textContent = data.unread;
                    } else {
                        chatBadge.style.display = 'none';
                    }
                }
                if (mobileChatBadge) {
                    if (data.unread > 0) {
                        mobileChatBadge.style.display = 'inline';
                        mobileChatBadge.textContent = data.unread > 99 ? '99+' : data.unread;
                    } else {
                        mobileChatBadge.style.display = 'none';
                    }
                }
            })
            .catch(() => {});
    }

    //* Start polling only if user is on chat page
    if (document.querySelector('.chat-container') || chatBadge) {
        //* Initial check
        updateUnreadCount();

        //* Check new messages every 5 seconds
        setInterval(checkNewMessages, 5000);

        //* Check unread every 15 seconds
        setInterval(updateUnreadCount, 15000);
    }

    //* ═══════════════════════════════════════════════════════════════════════════════
    //*  Auto-scroll chat down
    //* ═══════════════════════════════════════════════════════════════════════════════

    const chatMessages = document.querySelector('.chat-messages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    //* ═══════════════════════════════════════════════════════════════════════════════
    //*  Delete confirmation
    //* ═══════════════════════════════════════════════════════════════════════════════

    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', function (e) {
            if (!confirm(this.dataset.confirm || 'Вы уверены?')) {
                e.preventDefault();
            }
        });
    });

    //* ═══════════════════════════════════════════════════════════════════════════════
    //*  Autocomplete for teacher/student search
    //* ═══════════════════════════════════════════════════════════════════════════════

    function initAutocomplete(input, hiddenInput, role) {
        if (!input) return;
        let timeout = null;

        const wrapper = document.createElement('div');
        wrapper.style.position = 'relative';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const dropdown = document.createElement('div');
        dropdown.style.cssText = 'position:absolute;top:100%;left:0;right:0;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;max-height:200px;overflow-y:auto;z-index:300;display:none;box-shadow:0 4px 12px rgba(0,0,0,0.1)';
        wrapper.appendChild(dropdown);

        input.addEventListener('input', function () {
            clearTimeout(timeout);
            const val = this.value.trim();
            if (hiddenInput) hiddenInput.value = '';
            if (val.length < 1) {
                dropdown.style.display = 'none';
                return;
            }
            timeout = setTimeout(() => {
                fetch('/api/users/search?q=' + encodeURIComponent(val) + '&role=' + encodeURIComponent(role || ''))
                    .then(r => r.json())
                    .then(data => {
                        dropdown.innerHTML = '';
                        if (data.length === 0) {
                            dropdown.style.display = 'none';
                            return;
                        }
                        data.forEach(u => {
                            const item = document.createElement('div');
                            item.textContent = u.name;
                            item.style.cssText = 'padding:0.5rem 0.75rem;cursor:pointer;font-size:0.875rem;color:var(--text);transition:background.1s';
                            item.addEventListener('mouseenter', () => item.style.background = 'var(--bg-hover)');
                            item.addEventListener('mouseleave', () => item.style.background = 'transparent');
                            item.addEventListener('click', function () {
                                input.value = u.name;
                                if (hiddenInput) hiddenInput.value = u.id;
                                dropdown.style.display = 'none';
                            });
                            dropdown.appendChild(item);
                        });
                        dropdown.style.display = 'block';
                    })
                    .catch(() => { dropdown.style.display = 'none'; });
            }, 250);
        });

        input.addEventListener('blur', function () {
            setTimeout(() => { dropdown.style.display = 'none'; }, 200);
        });
        input.addEventListener('focus', function () {
            if (dropdown.children.length > 0) dropdown.style.display = 'block';
        });
    }

    document.querySelectorAll('[data-autocomplete]').forEach(el => {
        const role = el.dataset.autocomplete;
        const hiddenId = el.dataset.hiddenId;
        const hiddenEl = hiddenId ? document.getElementById(hiddenId) : null;
        initAutocomplete(el, hiddenEl, role);
    });

    //* ═══════════════════════════════════════════════════════════════════════════════
    //*  Modal windows
    //* ═══════════════════════════════════════════════════════════════════════════════

    document.querySelectorAll('[data-modal]').forEach(btn => {
        btn.addEventListener('click', function () {
            const modalId = this.dataset.modal;
            const modal = document.getElementById(modalId);
            if (modal) modal.classList.add('active');
        });
    });

    document.querySelectorAll('.modal-close, .modal').forEach(el => {
        el.addEventListener('click', function (e) {
            if (e.target === this || this.classList.contains('modal-close')) {
                const modal = this.closest('.modal');
                if (modal) {
                    modal.classList.remove('active');
                    modal.style.display = '';
                }
            }
        });
    });

    //* ═══════════════════════════════════════════════════════════════════════════════
    //*  DOCX generation (credentials)
    //* ═══════════════════════════════════════════════════════════════════════════════

    document.querySelectorAll('[data-export-docx]').forEach(btn => {
        btn.addEventListener('click', function () {
            const classId = this.dataset.classId;
            if (classId) {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '/admin/classes/' + classId + '/export-docx';
                document.body.appendChild(form);
                form.submit();
                document.body.removeChild(form);
            }
        });
    });


});
