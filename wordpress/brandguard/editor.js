(function (wp) {
    'use strict';
    const { createElement: el, useEffect, useRef, useState } = wp.element;
    const states = {
        APPROVED: 'Approved for this exact draft',
        NEEDS_REVIEW: 'Draft changed — needs review',
        PENDING_APPROVAL: 'Awaiting reviewer decision',
        REJECTED: 'Rejected',
        CHANGES_REQUESTED: 'Changes requested',
        NOT_SUBMITTED: 'Ready to send for review'
    };

    async function fingerprint(snapshot) {
        const encoder = new TextEncoder();
        const framed = Object.values(snapshot).map(value => {
            const text = String(value);
            return encoder.encode(text).length + ':' + text;
        }).join('');
        const digest = await crypto.subtle.digest('SHA-256', encoder.encode(framed));
        return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
    }

    function ReviewPanel() {
        const { id, title, content, excerpt, slug, featured_media } = wp.data.useSelect(select => {
            const editor = select('core/editor');
            const attr = key => editor.getEditedPostAttribute(key);
            return {
                id: editor.getCurrentPostId(), title: attr('title') || '',
                content: editor.getEditedPostContent() || '', excerpt: attr('excerpt') || '',
                slug: attr('slug') || '', featured_media: Number(attr('featured_media')) || 0
            };
        }, []);
        const encoded = JSON.stringify({ title, content, excerpt, slug, featured_media });
        const [result, setResult] = useState(null);
        const [busy, setBusy] = useState(false);
        const [refresh, setRefresh] = useState(0);
        const submitted = useRef(0);
        const path = '/brandguard/v1/posts/' + id;
        const current = result && result.encoded === encoded && result.id === id ? result : null;

        useEffect(() => {
            if (!id) return;
            let active = true, timer;
            async function check() {
                const generation = submitted.current;
                try {
                    const digest = await fingerprint(JSON.parse(encoded));
                    if (!active) return;
                    const reply = await wp.apiFetch({ path: path + '?digest=' + digest });
                    if (reply.digest !== digest || !states[reply.status]) throw new Error('Unexpected review response.');
                    if (active && generation === submitted.current) setResult({ ...reply, encoded, id });
                } catch (err) {
                    if (active && generation === submitted.current) setResult({ error: err.message, encoded, id });
                } finally {
                    if (active) timer = setTimeout(check, 15000);
                }
            }
            timer = setTimeout(check, 400);
            return () => { active = false; clearTimeout(timer); };
        }, [id, path, encoded, refresh]);

        async function send() {
            setBusy(true);
            submitted.current++;
            try {
                const snapshot = JSON.parse(encoded);
                const digest = await fingerprint(snapshot);
                const reply = await wp.apiFetch({ path, method: 'POST', data: { snapshot } });
                if (reply.digest !== digest || !states[reply.status]) throw new Error('The reviewed snapshot differs from the editor. Refresh and try again.');
                setResult({ ...reply, encoded, id });
            } catch (err) {
                setResult({ error: err.message, encoded, id });
            } finally {
                submitted.current++;
                setBusy(false);
                setRefresh(value => value + 1);
            }
        }

        const status = current?.error || states[current?.status] ||
            (result?.status === 'APPROVED' ? states.NEEDS_REVIEW : 'Checking current draft…');
        const panel = wp.editor.PluginDocumentSettingPanel;
        return el(panel, { name: 'brandguard-review', title: 'BrandGuard review' },
            el('p', { role: 'status' }, id ? status : 'Save the draft to enable review.'),
            current?.comment && el('p', null, current.comment),
            el('p', null, 'Reviews cover the title, block content, excerpt, slug and featured image selection.'),
            current?.review_url && el('p', null, el('a', {href: current.review_url, target: '_blank', rel: 'noopener noreferrer'}, 'Open review in BrandGuard')),
            el(wp.components.Button, { variant: 'secondary', disabled: !id || busy ||
                ['APPROVED', 'PENDING_APPROVAL', 'REJECTED', 'CHANGES_REQUESTED'].includes(current?.status), onClick: send },
                busy ? 'Sending…' : 'Send draft for review'),
            el(wp.components.Button, { variant: 'tertiary', disabled: !id || busy,
                onClick: () => setRefresh(value => value + 1) }, 'Refresh decision'));
    }

    wp.plugins.registerPlugin('brandguard-review', { render: ReviewPanel, icon: 'shield' });
})(window.wp);
