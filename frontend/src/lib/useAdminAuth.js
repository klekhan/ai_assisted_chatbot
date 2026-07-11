import { useCallback, useState } from "react";
import { adminGetStats } from "./api";

const STORAGE_KEY = "kb_admin_key";

export function useAdminAuth() {
  const [adminKey, setAdminKey] = useState(() => localStorage.getItem(STORAGE_KEY) || "");
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState(null);

  const login = useCallback(async (candidateKey) => {
    setVerifying(true);
    setError(null);
    try {
      await adminGetStats(candidateKey); // any admin call works as a verification ping
      localStorage.setItem(STORAGE_KEY, candidateKey);
      setAdminKey(candidateKey);
      return true;
    } catch (err) {
      setError(err.message.includes("401") || /invalid/i.test(err.message)
        ? "Incorrect admin key."
        : `Couldn't verify: ${err.message}`);
      return false;
    } finally {
      setVerifying(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setAdminKey("");
  }, []);

  return { adminKey, isAuthenticated: !!adminKey, login, logout, verifying, error };
}
