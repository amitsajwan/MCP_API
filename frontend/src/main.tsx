import React from 'react';
import { createRoot } from 'react-dom/client';
import { SimpleChatApp } from './ui/SimpleChatApp';

try {
	const container = document.getElementById('root');
	if (!container) throw new Error('Root element not found');
	createRoot(container).render(<SimpleChatApp />);
} catch (e) {
	console.error('App mount failed', e);
	const pre = document.createElement('pre');
	pre.style.color = 'red';
	pre.textContent = 'Mount error: ' + (e as Error).message;
	document.body.appendChild(pre);
}
