"use client";

import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  getCaptures,
  getPackets,
  getConversations,
  getEvidenceMap,
  getFrameDetail,
  getPayloadPreview,
  draftReport,
  updateReportSection,
  type CaptureArtifact,
  type PacketItem,
  type ConversationItem,
  type ImportDiagnosticError,
  type EvidenceCardItem,
  type ReportItem,
  type FrameDetail,
  type PayloadPreview,
} from "@/lib/api";
import UploadModal from "@/components/workspace/UploadModal";
import ImportDiagnosticModal from "@/components/workspace/ImportDiagnosticModal";
import DisplayFilter from "@/components/workspace/DisplayFilter";
import PacketTable from "@/components/workspace/PacketTable";
import DissectorTree from "@/components/workspace/DissectorTree";
import PayloadViewer from "@/components/workspace/PayloadViewer";
import ConversationsList from "@/components/workspace/ConversationsList";
import AIPanel from "@/components/workspace/AIPanel";
import ReportBuilder from "@/components/workspace/ReportBuilder";
import CaptureLifecycleModal from "@/components/workspace/CaptureLifecycleModal";

export default function WorkspacePage() {
  const { user, token, setToken, loading: authLoading } = useAuth();
  const router = useRouter();

  const [captures, setCaptures] = useState<CaptureArtifact[]>([]);
  const [selectedCapture, setSelectedCapture] = useState<CaptureArtifact | null>(null);

  const [packets, setPackets] = useState<PacketItem[]>([]);
  const [selectedPacket, setSelectedPacket] = useState<PacketItem | null>(null);
  const [frameDetail, setFrameDetail] = useState<FrameDetail | null>(null);
  const [payloadPreview, setPayloadPreview] = useState<PayloadPreview | null>(null);
  const [loadingPackets, setLoadingPackets] = useState(false);

  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [claims, setClaims] = useState<EvidenceCardItem[]>([]);
  const [report, setReport] = useState<ReportItem | null>(null);

  const [activeTab, setActiveTab] = useState<"packets" | "conversations" | "report">("packets");
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isLifecycleOpen, setIsLifecycleOpen] = useState(false);
  const [isAIPanelOpen, setIsAIPanelOpen] = useState(true);
  const [diagnosticErr, setDiagnosticErr] = useState<ImportDiagnosticError | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [authLoading, user, router]);

  useEffect(() => {
    if (token && user) {
      fetchCapturesList();
    }
  }, [token, user]);

  useEffect(() => {
    if (token && selectedCapture) {
      fetchCaptureData(selectedCapture.id);
    }
  }, [token, selectedCapture]);

  useEffect(() => {
    let active = true;
    if (token && selectedCapture && selectedPacket) {
      getFrameDetail(token, selectedCapture.id, selectedPacket.frame_number)
        .then((d) => {
          if (active) setFrameDetail(d);
        })
        .catch(() => {
          if (active) setFrameDetail(null);
        });
      getPayloadPreview(token, selectedCapture.id, selectedPacket.frame_number)
        .then((p) => {
          if (active) setPayloadPreview(p);
        })
        .catch(() => {
          if (active) setPayloadPreview(null);
        });
    }
    return () => {
      active = false;
    };
  }, [token, selectedCapture, selectedPacket]);

  async function fetchCapturesList() {
    try {
      const list = await getCaptures(token!);
      setCaptures(list);
      if (list.length > 0 && !selectedCapture) {
        setSelectedCapture(list[0]);
      }
    } catch {
      // handled
    }
  }

  async function fetchCaptureData(artifactId: number) {
    setLoadingPackets(true);
    try {
      const pkts = await getPackets(token!, artifactId);
      setPackets(pkts);
      if (pkts.length > 0) setSelectedPacket(pkts[0]);
      setLoadingPackets(false);
    } catch {
      setLoadingPackets(false);
    }

    try {
      const convs = await getConversations(token!, artifactId);
      setConversations(convs);
    } catch {
      // handled
    }

    try {
      const emap = await getEvidenceMap(token!, artifactId);
      setClaims(emap.claims || []);
      if (emap.id) {
        const rep = await draftReport(token!, emap.id);
        setReport(rep);
      }
    } catch {
      // handled
    }
  }

  async function handleApplyFilter(filter: string) {
    if (!selectedCapture) return;
    setLoadingPackets(true);
    try {
      const pkts = await getPackets(token!, selectedCapture.id, filter);
      setPackets(pkts);
      if (pkts.length > 0) setSelectedPacket(pkts[0]);
      setLoadingPackets(false);
    } catch {
      setLoadingPackets(false);
    }
  }

  async function handleUpdateReportSection(
    sectionId: number,
    updates: { title?: string; content?: string }
  ) {
    try {
      const updatedSec = await updateReportSection(token!, sectionId, updates);
      if (report) {
        setReport({
          ...report,
          sections: report.sections.map((s) => (s.id === sectionId ? updatedSec : s)),
        });
      }
    } catch {
      // handled
    }
  }

  function handleNavigateLink(link: string) {
    // Parse smartshark:// frame or conv deep links
    if (link.includes("/frame/")) {
      const frameNum = parseInt(link.split("/frame/")[1], 10);
      const targetPkt = packets.find((p) => p.frame_number === frameNum);
      if (targetPkt) {
        setSelectedPacket(targetPkt);
        setActiveTab("packets");
      }
    }
  }

  if (authLoading || !user) return null;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top Navbar */}
      <nav className="bg-white shadow z-10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 justify-between">
            <div className="flex items-center gap-8">
              <h1 className="text-xl font-bold text-gray-900">Smartshark</h1>
              <div className="flex gap-4">
                <span className="text-blue-600 font-semibold border-b-2 border-blue-600 py-4">
                  Workspace
                </span>
                {user.role === "admin" && (
                  <span
                    className="text-gray-700 hover:text-gray-900 cursor-pointer py-4"
                    onClick={() => router.push("/admin/settings")}
                  >
                    Admin Settings
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-500">
                {user.username} ({user.role})
              </span>
              <button
                onClick={() => {
                  setToken(null);
                  router.push("/login");
                }}
                className="rounded-md bg-gray-100 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-200"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col overflow-y-auto p-6 max-w-7xl mx-auto w-full space-y-6">
          {/* Action Bar & Capture Selector */}
          <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-lg shadow-sm border">
            <div className="flex items-center gap-3">
              <span className="font-semibold text-sm text-gray-700">Capture File:</span>
              <select
                value={selectedCapture?.id || ""}
                onChange={(e) => {
                  const cap = captures.find((c) => c.id === parseInt(e.target.value, 10));
                  if (cap) setSelectedCapture(cap);
                }}
                className="rounded border border-gray-300 px-3 py-1.5 text-sm font-medium focus:border-blue-500 focus:outline-none"
              >
                {captures.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.original_filename} ({c.status})
                  </option>
                ))}
                {captures.length === 0 && <option value="">No PCAPs uploaded</option>}
              </select>

              <button
                onClick={() => setIsLifecycleOpen(true)}
                className="rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
              >
                ⚙ Manage Captures
              </button>
            </div>

            <button
              onClick={() => setIsUploadOpen(true)}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              + Upload PCAP
            </button>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-gray-200 gap-6 text-sm font-medium">
            <button
              onClick={() => setActiveTab("packets")}
              className={`pb-3 border-b-2 ${
                activeTab === "packets"
                  ? "border-blue-600 text-blue-600 font-bold"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              Packets & Dissector ({packets.length})
            </button>
            <button
              onClick={() => setActiveTab("conversations")}
              className={`pb-3 border-b-2 ${
                activeTab === "conversations"
                  ? "border-blue-600 text-blue-600 font-bold"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              Conversations Stream ({conversations.length})
            </button>
            <button
              onClick={() => setActiveTab("report")}
              className={`pb-3 border-b-2 ${
                activeTab === "report"
                  ? "border-blue-600 text-blue-600 font-bold"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              Investigation Report Builder
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === "packets" && (
            <div className="space-y-4">
              <DisplayFilter onApplyFilter={handleApplyFilter} loading={loadingPackets} />
              <PacketTable
                packets={packets}
                selectedFrame={selectedPacket?.frame_number || null}
                onSelectPacket={setSelectedPacket}
                loading={loadingPackets}
              />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <DissectorTree packet={selectedPacket} frameDetail={frameDetail} />
                <PayloadViewer packet={selectedPacket} payload={payloadPreview} />
              </div>
            </div>
          )}

          {activeTab === "conversations" && (
            <ConversationsList conversations={conversations} />
          )}

          {activeTab === "report" && (
            <ReportBuilder
              report={report}
              onUpdateSection={handleUpdateReportSection}
              onExportMarkdown={() => alert("Report exported to Markdown!")}
              onExportPDF={() => alert("Report exported to PDF!")}
            />
          )}
        </div>

        {/* AI Investigation Panel */}
        <AIPanel
          isOpen={isAIPanelOpen}
          onToggle={() => setIsAIPanelOpen(!isAIPanelOpen)}
          claims={claims}
          onNavigateLink={handleNavigateLink}
        />
      </div>

      {/* Modals */}
      <UploadModal
        token={token!}
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={(newCap) => {
          setCaptures((prev) => [newCap, ...prev]);
          setSelectedCapture(newCap);
        }}
        onErrorDiagnostic={setDiagnosticErr}
      />

      <ImportDiagnosticModal
        diagnostic={diagnosticErr}
        onClose={() => setDiagnosticErr(null)}
      />

      <CaptureLifecycleModal
        token={token!}
        captures={captures}
        isOpen={isLifecycleOpen}
        onClose={() => setIsLifecycleOpen(false)}
        onRefresh={fetchCapturesList}
      />
    </div>
  );
}
