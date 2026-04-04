/**
 * services/message-handler.js
 * ─────────────────────────────────────────
 * Routes incoming messages to appropriate handlers
 * based on session state and command type.
 */

import SessionManager from './session-manager.js';
import Messages from '../config/messages.json' with { type: 'json' };
import { handleOnboarding } from '../handlers/onboarding.js';
import { handleCommand } from '../handlers/commands.js';

/**
 * Main message router
 */
export async function routeMessage(phone, messageBody) {
  const message = messageBody.trim().toUpperCase();
  const session = SessionManager.getOrCreateSession(phone);
  const lang = session.language;

  // ──────────────────────────────────────────────────────────────
  // COMMAND ROUTING (always available, regardless of onboarding state)
  // ──────────────────────────────────────────────────────────────

  if (message === 'HELP') {
    return getLocalizedMessage('help', lang);
  }

  if (message === 'LANG') {
    return getLocalizedMessage('welcome', lang);
  }

  if (message === 'STATUS' && session.isOnboarded) {
    return await handleCommand(phone, 'STATUS', session);
  }

  if (message === 'RENEW' && session.isOnboarded) {
    return await handleCommand(phone, 'RENEW', session);
  }

  if (message === 'SHIFT' && session.isOnboarded) {
    return await handleCommand(phone, 'SHIFT', session);
  }

  if (message === 'APPEAL' && session.isOnboarded) {
    return await handleCommand(phone, 'APPEAL', session);
  }

  // ──────────────────────────────────────────────────────────────
  // ONBOARDING FLOW
  // ──────────────────────────────────────────────────────────────

  if (message === 'JOIN') {
    if (session.isOnboarded) {
      return getLocalizedMessage('already_onboarded', lang);
    }
    SessionManager.updateSession(phone, { onboardingStep: 'language' });
    return getLocalizedMessage('welcome', 'en'); // Always show in English first
  }

  // If user hasn't started onboarding, guide them
  if (!session.isOnboarded && session.onboardingStep === 'start') {
    return `👋 Hello! Type *JOIN* to start your GigKavach registration.\n\nGigKavach provides automatic income protection during disruptions—no claims to file, just automatic payouts.`;
  }

  // Route to onboarding handler based on current step
  return await handleOnboarding(phone, message, session);
}

/**
 * Get localized message by key and language
 */
export function getLocalizedMessage(messageKey, language = 'en', substitutions = {}) {
  const messages = Messages[messageKey];

  if (!messages) {
    console.error(`No message template found for key: ${messageKey}`);
    return `⚠️ Message template not found: ${messageKey}`;
  }

  let text = messages[language] || messages['en'];

  // Replace all placeholders {variable} with values
  Object.entries(substitutions).forEach(([key, value]) => {
    text = text.replace(new RegExp(`{${key}}`, 'g'), value);
  });

  return text;
}
