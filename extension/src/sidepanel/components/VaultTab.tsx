import { useState } from "react";
import type { AnalyzeResponse, VaultReceipt } from "../../shared/types";
import { vaultAnalysis } from "../../shared/api";

interface VaultTabProps {
  data: AnalyzeResponse;
}

function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
      />
    </svg>
  );
}

function LockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
      />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function truncateHash(hash: string) {
  return hash.slice(0, 10) + "..." + hash.slice(-10);
}

function truncateAddress(addr: string) {
  return addr.slice(0, 14) + "..." + addr.slice(-8);
}

export default function VaultTab({ data }: VaultTabProps) {
  const [receipt, setReceipt] = useState<VaultReceipt | null>(null);
  const [sealing, setSealing] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState<string | null>(null);

  const handleVault = async () => {
    setSealing(true);
    setError("");
    try {
      const analysisPayload: Record<string, unknown> = {
        summary: data.summary,
        key_points: data.key_points,
        risks: data.risks,
        entities: data.entities,
      };
      const result = await vaultAnalysis(analysisPayload);
      setReceipt(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to vault analysis");
    } finally {
      setSealing(false);
    }
  };

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  };

  if (receipt) {
    return (
      <div className="space-y-4">
        {/* Sealed banner */}
        <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl border border-emerald-200 p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
              <CheckCircleIcon className="w-6 h-6 text-emerald-600" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-emerald-800">Quantum Vault Sealed</h2>
              <p className="text-xs text-emerald-600">
                Protected by post-quantum lattice encryption
              </p>
            </div>
          </div>
          <p className="text-sm text-emerald-700 leading-relaxed">{receipt.message}</p>
        </div>

        {/* Receipt details */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            Vault Receipt
          </h2>

          <div className="space-y-3">
            <ReceiptRow
              label="Vault ID"
              value={receipt.vault_id}
              fullValue={receipt.vault_id}
              onCopy={handleCopy}
              copied={copied}
              mono
            />
            <ReceiptRow
              label="Content Hash"
              value={truncateHash(receipt.content_hash)}
              fullValue={receipt.content_hash}
              onCopy={handleCopy}
              copied={copied}
              mono
            />
            <ReceiptRow
              label="Vault Address"
              value={truncateAddress(receipt.vault_address)}
              fullValue={receipt.vault_address}
              onCopy={handleCopy}
              copied={copied}
              mono
            />
            <ReceiptRow
              label="Network"
              value={receipt.network}
              fullValue={receipt.network}
              onCopy={handleCopy}
              copied={copied}
            />
            <ReceiptRow
              label="Algorithm"
              value={receipt.algorithm}
              fullValue={receipt.algorithm}
              onCopy={handleCopy}
              copied={copied}
            />
            <ReceiptRow
              label="Sealed At"
              value={new Date(receipt.timestamp).toLocaleString()}
              fullValue={receipt.timestamp}
              onCopy={handleCopy}
              copied={copied}
            />
            <div className="flex items-center gap-2 pt-1">
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                {receipt.status}
              </span>
            </div>
          </div>
        </div>

        {/* Vault another */}
        <button
          onClick={() => setReceipt(null)}
          className="w-full py-2.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors"
        >
          Vault Another Analysis
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Info card */}
      <div className="bg-gradient-to-br from-violet-50 to-indigo-50 rounded-xl border border-violet-200 p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-full bg-violet-100 flex items-center justify-center">
            <ShieldIcon className="w-6 h-6 text-violet-600" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-violet-800">Abelian Privacy Vault</h2>
            <p className="text-xs text-violet-600">Quantum-Resistant Document Protection</p>
          </div>
        </div>
        <p className="text-sm text-violet-700 leading-relaxed">
          Seal your contract analysis with post-quantum lattice-based encryption on the
          Abelian network. Your data stays private -- not even quantum computers can
          break the seal.
        </p>
      </div>

      {/* What gets vaulted */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          What Gets Vaulted
        </h2>
        <ul className="space-y-2">
          {[
            "Contract summary & key points",
            "Risk flags & clause excerpts",
            "Extracted entities (parties, dates, amounts)",
          ].map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
              <LockIcon className="w-4 h-4 mt-0.5 text-violet-500 shrink-0" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Vault button */}
      <button
        onClick={handleVault}
        disabled={sealing}
        className="w-full py-3 px-4 rounded-xl text-white font-semibold text-sm
          bg-gradient-to-r from-violet-600 to-indigo-600
          hover:from-violet-700 hover:to-indigo-700
          disabled:opacity-60 disabled:cursor-not-allowed
          transition-all shadow-lg shadow-violet-200 flex items-center justify-center gap-2"
      >
        {sealing ? (
          <>
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Sealing to Quantum Vault...
          </>
        ) : (
          <>
            <ShieldIcon className="w-5 h-5" />
            Lock to Quantum Vault
          </>
        )}
      </button>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Footer badge */}
      <div className="text-center pt-2">
        <span className="inline-flex items-center gap-1.5 text-xs text-gray-400">
          <ShieldIcon className="w-3.5 h-3.5" />
          Powered by Abelian Foundation &middot; QDay Track
        </span>
      </div>
    </div>
  );
}

function ReceiptRow({
  label,
  value,
  fullValue,
  onCopy,
  copied,
  mono,
}: {
  label: string;
  value: string;
  fullValue: string;
  onCopy: (text: string, label: string) => void;
  copied: string | null;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div className="min-w-0">
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
          {label}
        </span>
        <p
          className={`text-sm text-gray-800 break-all ${mono ? "font-mono" : ""}`}
        >
          {value}
        </p>
      </div>
      <button
        onClick={() => onCopy(fullValue, label)}
        className="shrink-0 mt-4 p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
        title={`Copy ${label}`}
      >
        {copied === label ? (
          <CheckCircleIcon className="w-3.5 h-3.5 text-emerald-500" />
        ) : (
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
        )}
      </button>
    </div>
  );
}
