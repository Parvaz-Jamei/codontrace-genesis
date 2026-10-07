import { useState, useEffect } from 'react';

// Define the BeforeInstallPromptEvent interface since it's not standard in TypeScript's DOM library yet
export interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
  prompt(): Promise<void>;
}

declare global {
  interface Window {
    deferredPrompt: BeforeInstallPromptEvent | null;
  }
}

export function useInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(
    () => typeof window !== 'undefined' ? window.deferredPrompt : null
  );

  useEffect(() => {
    // Check again when the component mounts in case it missed the initial event
    if (typeof window !== 'undefined' && window.deferredPrompt && !deferredPrompt) {
      setDeferredPrompt(window.deferredPrompt);
    }

    const handler = (e: Event) => {
      // Prevent the mini-infobar from appearing on mobile
      e.preventDefault();
      // Stash the event so it can be triggered later.
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      if (typeof window !== 'undefined') {
        window.deferredPrompt = e as BeforeInstallPromptEvent;
      }
    };

    window.addEventListener('beforeinstallprompt', handler);

    return () => {
      window.removeEventListener('beforeinstallprompt', handler);
    };
  }, [deferredPrompt]);

  const promptToInstall = async () => {
    if (!deferredPrompt) {
      return;
    }
    // Show the install prompt
    await deferredPrompt.prompt();
    // Wait for the user to respond to the prompt
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      console.log('User accepted the install prompt');
    } else {
      console.log('User dismissed the install prompt');
    }
    // We've used the prompt, and can't use it again, throw it away
    setDeferredPrompt(null);
    if (typeof window !== 'undefined') {
      window.deferredPrompt = null;
    }
  };

  return { isInstallable: !!deferredPrompt, promptToInstall };
}
