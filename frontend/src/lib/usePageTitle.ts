import { useEffect } from 'react';

/**
 * Simple hook to set the document title with an optional suffix.
 * Usage: usePageTitle('Register') -> "Register | EcoLearn"
 */
export default function usePageTitle(title: string, suffix = 'EcoLearn') {
  useEffect(() => {
    const parts = [title, suffix].filter(Boolean);
    document.title = parts.join(' | ');
  }, [title, suffix]);
}
