import { useState, useEffect, useRef } from 'react';
import { Upload, ArrowUp, Filter, FileText, Globe, BookOpen, X } from 'lucide-react';
import {API_BASE_URL} from '../config';

export default function App() {
    // State management
    const [systemStatus, setSystemStatus] = useState({
        ready: false,
        current_step: "Connecting....",
        progress: 0
    })

    // Ingestion UI states
    const [ingestMode, setIngestMode] = useState('file'); // 'file', 'url', 'arxiv'
    const [urlInput, setUrlInput] = useState("");
    const [arxivQuery, setArxivQuery] = useState("");
    const [arxivResults, setArxivResults] = useState([]);

    // Chat States
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState("");
    const [isTyping, setIsTyping] = useState(false);

    // Upload States
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState(null);

    const chatEndRef = useRef(null);
    const [uploadedDocs, setUploadedDocs] = useState([]);

    const [selectedFileTypes, setSelectedFileTypes] = useState([]);
    const [showFilterMenu, setShowFilterMenu] = useState(false);
    const filterMenuRef = useRef(null);

    const availableFileTypes = Array.from(
        new Set(uploadedDocs.map(doc => doc.name.split('.').pop().toLowerCase()))
    );

    // Backend loading status
    useEffect(() => {
        console.log("1. useEffect has mounted successfully!");
        let pollingInterval = null;

        const checkStatus = async () => {
            console.log("2. checkStatus function is executing...");
            try {
                console.log("📡 3. Attempting to fetch from backend...");
                const res = await fetch(`${API_BASE_URL}/api/status`);

                console.log("4. Fetch response received. Status code:", res.status);
                if (res.ok) {
                    const data = await res.json();
                    console.log("5. Parsed JSON payload:", data);

                    setSystemStatus(data);

                    if (data.ready && pollingInterval) {
                        console.log("6. System is ready! Clearing interval.");
                        clearInterval(pollingInterval);
                    }
                }
            } catch (error) {
                console.error("CRASH INSIDE CATCH BLOCK:", error);
                setSystemStatus({
                    ready: false,
                    current_step: "Waiting for server to start...",
                    progress: 0
                });
            }
        };

        checkStatus();
        pollingInterval = setInterval(checkStatus, 1000);

        return () => {
            if (pollingInterval) clearInterval(pollingInterval);
        };
    }, []);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behaviour: "smooth" });
    }, [messages]);

    // Close filter menu on outside click
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (filterMenuRef.current && !filterMenuRef.current.contains(event.target)) {
                setShowFilterMenu(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Handling file uploads
    const handleFileChange = (e) => {
        setSelectedFiles(e.target.files);
        setUploadStatus(null);
    }

    const handleUpload = async (e) => {
        e.preventDefault();
        if (selectedFiles.length === 0) return;

        console.log(import.meta.env.VITE_API_TOKEN)

        setIsUploading(true);
        setUploadStatus("Uploading & Processing....")

        const formData = new FormData();
        for (let i = 0; i < selectedFiles.length; i++) {
            formData.append("files", selectedFiles[i]);
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/upload`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${import.meta.env.VITE_API_TOKEN}`
                },
                body: formData
            });

            const data = await response.json();
            if (response.ok) {
                setUploadStatus(`Success: ${data.chunks_created} chunks added!`);

                // Generates local browser links for the uploaded files
                const newDocs = Array.from(selectedFiles).map(file => ({
                    name: file.name,
                    url: URL.createObjectURL(file)
                }));

                setUploadedDocs(prev => [...prev, ...newDocs])

                setSelectedFiles([]);

                document.getElementById('file-upload').value = '';
            } else {
                setUploadStatus(`Error: ${data.detail}`);
            }
        } catch (error) {
            setUploadStatus(`Upload failed: Could not reach the backend`);
        } finally {
            setIsUploading(false);
        }
    };

    const handleUrlLoad = async (e) => {
        e.preventDefault();
        if (!urlInput.trim()) return;
        
        setIsUploading(true);
        setUploadStatus("Scraping and processing URL...");

        try {
            const response = await fetch(`${API_BASE_URL}/api/url/load`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${import.meta.env.VITE_API_TOKEN}`
                },
                body: JSON.stringify({ urls: [urlInput.trim()] })
            });
            const data = await response.json();
            
            if (response.ok) {
                setUploadStatus(`Success: ${data.chunks_created} chunks added from Web!`);
                setUploadedDocs(prev => [...prev, { name: urlInput, url: urlInput }]);
                setUrlInput("");
            } else setUploadStatus(`Error: ${data.detail}`);
        } catch (error) {
            setUploadStatus("Failed to reach backend.");
        } finally {
            setIsUploading(false);
        }
    };

    const handleArxivSearch = async (e) => {
        e.preventDefault();
        if (!arxivQuery.trim()) return;
        
        setUploadStatus("Searching Arxiv...");
        try {
            const response = await fetch(`${API_BASE_URL}/api/arxiv/search`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${import.meta.env.VITE_API_TOKEN}`
                },
                body: JSON.stringify({ query: arxivQuery.trim() })
            });
            const data = await response.json();
            if (response.ok) {
                setArxivResults(data.results);
                setUploadStatus(null);
            } else setUploadStatus(`Error: ${data.detail}`);
        } catch (error) {
            setUploadStatus("Search failed.");
        }
    };

    const handleArxivLoad = async (paperId, paperTitle, pdfUrl) => {
        setIsUploading(true);
        setUploadStatus(`Downloading and processing ${paperId}...`);

        try {
            const response = await fetch(`${API_BASE_URL}/api/arxiv/load`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${import.meta.env.VITE_API_TOKEN}`
                },
                body: JSON.stringify({ paper_ids: [paperId] })
            });
            const data = await response.json();
            
            if (response.ok) {
                setUploadStatus(`Success: ${data.chunks_created} chunks added from Arxiv!`);
                setUploadedDocs(prev => [...prev, { name: `Arxiv: ${paperTitle}`, url: pdfUrl }]);
            } else setUploadStatus(`Error: ${data.detail}`);
        } catch (error) {
            setUploadStatus("Failed to reach backend.");
        } finally {
            setIsUploading(false);
        }
    };

    // Handling chat submission
    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!inputValue.trim() || isTyping) return;

        const userText = inputValue.trim();
        setInputValue("");
        setIsTyping(true);

        // Add user message to UI
        const updatedMessages = [...messages, { role: "user", content: userText }];
        setMessages(updatedMessages);

        // Format the session history for the stateless backend
        const historyString = messages
            .map(msg => `${msg.role === "user" ? "User" : "AI"}: ${msg.content}`)
            .join("\n")

        try {
            const response = await fetch(`${API_BASE_URL}/api/chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${import.meta.env.VITE_API_TOKEN}`
                },
                body: JSON.stringify({
                    query: userText,
                    chat_history: historyString,
                    file_types: selectedFileTypes.length > 0 ? selectedFileTypes : null
                })
            });
            const data = await response.json();

            if (response.ok) {
                setMessages(prev => [...prev, { role: "ai", content: data.answer }]);
            } else {
                setMessages(prev => [...prev, { role: "ai", content: `Error ${data.detail}` }]);
            }
        } catch (error) {
            setMessages(prev => [...prev, { role: "ai", content: "Network error: Could not reach the backend" }])
        }
        finally {
            setIsTyping(false);
        }
    };

    // Remove document from list
    const removeDocument = (index) => {
        setUploadedDocs(prev => prev.filter((_, i) => i !== index));
    };

    // UI Render: Loading Screen
    if (!systemStatus.ready) {
        return (
            <div className="flex items-center justify-center h-screen bg-black">
                <div className="text-center p-12 rounded-3xl bg-gradient-to-br from-neutral-950 to-neutral-900 border border-white/10 shadow-2xl max-w-md w-full mx-4 backdrop-blur-sm">
                    <div className="mb-8">
                        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-white to-neutral-300 flex items-center justify-center shadow-lg">
                            <div className="w-12 h-12 rounded-full bg-slate-900 flex items-center justify-center animate-spin">
                                <div className="w-8 h-8 rounded-full border-2 border-neutral-700 border-t-white"></div>
                            </div>
                        </div>
                    </div>
                    <h2 className="text-3xl font-bold text-white mb-3">Initializing AI Core</h2>
                    <p className="text-neutral-300 mb-8">{systemStatus.current_step}</p>
                    <div className="w-full bg-neutral-800 rounded-full h-2.5 mb-4 overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-white to-neutral-400 transition-all duration-300 shadow-lg"
                            style={{ width: `${systemStatus.progress}%` }}
                        ></div>
                    </div>
                    <p className="text-neutral-400 text-sm font-medium">{systemStatus.progress}%</p>
                </div>
            </div>
        )
    }

    // UI Render: Active chat interface
    return (
        <div className="flex h-screen bg-black overflow-hidden text-white">

            {/* LEFT SIDEBAR: Knowledge Base Panel */}
            <aside className="w-96 bg-gradient-to-b from-neutral-950 to-neutral-900 border-r border-white/10 flex flex-col overflow-hidden shadow-lg">

                {/* Sidebar Header */}
                <div className="p-6 border-b border-white/10 bg-gradient-to-r from-neutral-950 to-neutral-900">
                    <h2 className="text-xl font-bold text-white mb-2">Knowledge Base</h2>
                    <p className="text-sm text-neutral-400">Upload documents to enhance context</p>
                </div>

                {/* Scrollable Content Area */}
                <div className="flex-1 overflow-y-auto">
                    
                    {/* Ingestion Control Card */}
                    <div className="p-6 m-4 rounded-xl bg-neutral-900 border border-white/10 shadow-md">
                        <h3 className="text-sm font-semibold text-neutral-300 mb-4 uppercase tracking-wide">Ingestion Control</h3>

                        {/* Tab Navigation */}
                        <div className="flex gap-3 mb-6">
                            <button
                                onClick={() => setIngestMode('file')}
                                className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-semibold transition-all duration-200 ${
                                    ingestMode === 'file'
                                        ? 'bg-white text-black shadow-lg shadow-white/20'
                                        : 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700 hover:text-white'
                                }`}
                            >
                                <FileText className="w-4 h-4 inline mr-2" />Files
                            </button>
                            <button
                                onClick={() => setIngestMode('url')}
                                className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-semibold transition-all duration-200 ${
                                    ingestMode === 'url'
                                        ? 'bg-white text-black shadow-lg shadow-white/20'
                                        : 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700 hover:text-white'
                                }`}
                            >
                                <Globe className="w-4 h-4 inline mr-2" />Web
                            </button>
                            <button
                                onClick={() => setIngestMode('arxiv')}
                                className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-semibold transition-all duration-200 ${
                                    ingestMode === 'arxiv'
                                        ? 'bg-white text-black shadow-lg shadow-white/20'
                                        : 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700 hover:text-white'
                                }`}
                            >
                                <BookOpen className="w-4 h-4 inline mr-2" />Arxiv
                            </button>
                        </div>

                        {/* FILE UPLOAD TAB */}
                        {ingestMode === 'file' && (
                            <form onSubmit={handleUpload} className="space-y-4">
                                <label className="flex flex-col items-center justify-center p-8 rounded-2xl border-2 border-dashed border-white/15 hover:border-white/35 cursor-pointer transition-all hover:bg-white/5 group">
                                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-white/10 to-neutral-700/20 flex items-center justify-center mb-3 group-hover:from-white/15 group-hover:to-neutral-700/30 transition-all">
                                        <Upload className="w-6 h-6 text-white/70 group-hover:text-white transition-colors" />
                                    </div>
                                    <span className="text-sm font-semibold text-white">Click to upload files</span>
                                    <span className="text-xs text-neutral-400 mt-1">or drag and drop</span>
                                    <input
                                        id="file-upload"
                                        type="file"
                                        multiple
                                        onChange={handleFileChange}
                                        disabled={isUploading}
                                        className="hidden"
                                    />
                                </label>
                                {selectedFiles.length > 0 && (
                                    <div className="text-xs text-neutral-300 font-medium">
                                        ✓ {selectedFiles.length} file(s) selected
                                    </div>
                                )}
                                <button
                                    type="submit"
                                    disabled={isUploading || selectedFiles.length === 0}
                                    className="w-full py-2.5 px-4 rounded-lg bg-white hover:bg-neutral-200 disabled:bg-neutral-700 disabled:cursor-not-allowed text-black text-sm font-semibold transition-all shadow-lg hover:shadow-white/20 disabled:shadow-none"
                                >
                                    {isUploading ? "Processing..." : "Upload to Vector DB"}
                                </button>
                            </form>
                        )}

                        {/* WEB URL TAB */}
                        {ingestMode === 'url' && (
                            <form onSubmit={handleUrlLoad} className="space-y-4">
                                <input
                                    type="url"
                                    value={urlInput}
                                    onChange={(e) => setUrlInput(e.target.value)}
                                    placeholder="https://example.com"
                                    disabled={isUploading}
                                    className="w-full px-4 py-3 rounded-lg bg-neutral-800 border border-white/10 text-white placeholder-neutral-500 focus:border-white/30 focus:ring-2 focus:ring-white/10 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                                    required
                                />
                                <button
                                    type="submit"
                                    disabled={isUploading || !urlInput}
                                    className="w-full py-2.5 px-4 rounded-lg bg-white hover:bg-neutral-200 disabled:bg-neutral-700 disabled:cursor-not-allowed text-black text-sm font-semibold transition-all shadow-lg hover:shadow-white/20 disabled:shadow-none"
                                >
                                    {isUploading ? "Processing..." : "Ingest Webpage"}
                                </button>
                            </form>
                        )}

                        {/* ARXIV SEARCH TAB */}
                        {ingestMode === 'arxiv' && (
                            <div className="space-y-4">
                                <form onSubmit={handleArxivSearch} className="flex gap-2">
                                    <input
                                        type="text"
                                        value={arxivQuery}
                                        onChange={(e) => setArxivQuery(e.target.value)}
                                        placeholder="Search papers..."
                                            className="flex-1 px-4 py-2 rounded-lg bg-neutral-800 border border-white/10 text-white placeholder-neutral-500 focus:border-white/30 focus:ring-2 focus:ring-white/10 focus:outline-none transition-all text-sm"
                                    />
                                    <button type="submit" className="px-4 py-2 rounded-lg bg-neutral-800 hover:bg-neutral-700 border border-white/10 text-neutral-300 hover:text-white transition-all">
                                        🔍
                                    </button>
                                </form>

                                {/* Arxiv Results */}
                                <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
                                    {arxivResults.map(paper => (
                                        <div key={paper.id} className="p-4 rounded-xl bg-gradient-to-br from-neutral-900 to-neutral-800 border border-white/10 hover:border-white/25 hover:shadow-lg transition-all">
                                            <p className="text-sm font-semibold text-white mb-1 line-clamp-2">{paper.title}</p>
                                            <p className="text-xs text-neutral-400 mb-3">{paper.published} • {paper.authors[0]}</p>
                                            <button
                                                onClick={() => handleArxivLoad(paper.id, paper.title, paper.pdf_url)}
                                                disabled={isUploading}
                                                className="w-full py-1.5 px-3 rounded-lg bg-white hover:bg-neutral-200 disabled:bg-neutral-700 disabled:cursor-not-allowed text-black text-xs font-semibold transition-all shadow-md hover:shadow-white/20 disabled:shadow-none"
                                            >
                                                Ingest Paper
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Upload Status Alert */}
                    {uploadStatus && (
                        <div className="mx-5 mb-5 p-4 rounded-xl bg-gradient-to-r from-neutral-900 to-neutral-800 border border-white/10 text-neutral-200 text-sm font-medium shadow-lg animate-fade-in">
                            {uploadStatus}
                        </div>
                    )}

                    {/* Active Documents Section */}
                    {uploadedDocs.length > 0 && (
                        <div className="p-5 m-5 rounded-2xl bg-gradient-to-br from-neutral-900 to-neutral-800 border border-white/10 shadow-xl">
                            <h3 className="text-sm font-semibold text-neutral-300 mb-4 uppercase tracking-widest">Active Documents ({uploadedDocs.length})</h3>
                            <div className="space-y-2 max-h-64 overflow-y-auto pr-2">
                                {uploadedDocs.map((doc, idx) => (
                                    <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-neutral-800/70 hover:bg-neutral-700/70 border border-white/10 hover:border-white/25 transition-all group">
                                        <a
                                            href={doc.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex items-center gap-3 flex-1 min-w-0"
                                        >
                                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-white/10 to-neutral-700/20 flex items-center justify-center flex-shrink-0">
                                                <FileText className="w-4 h-4 text-white/70" />
                                            </div>
                                            <span className="text-sm text-neutral-300 truncate hover:text-white transition-colors">{doc.name}</span>
                                        </a>
                                        <button
                                            onClick={() => removeDocument(idx)}
                                            className="ml-2 p-1 rounded-lg hover:bg-white/10 text-neutral-400 hover:text-white transition-all opacity-0 group-hover:opacity-100"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                </div>
            </aside>

            {/* RIGHT MAIN PANEL: Chat Workspace */}
            <main className="flex-1 flex flex-col min-h-0 overflow-hidden bg-black">

                {/* Chat Container */}
                <div className="flex-1 flex flex-col min-h-0 bg-transparent">

                    {/* Header */}
                    <div className="px-8 py-7 border-b border-white/10 bg-gradient-to-r from-neutral-950/60 to-neutral-900/80 backdrop-blur-md">
                        <h2 className="text-2xl font-bold bg-gradient-to-r from-white to-neutral-300 bg-clip-text text-transparent">Research Assistant</h2>
                        <p className="text-sm text-neutral-400 mt-1">Ask questions about your uploaded documents</p>
                    </div>

                    {/* Messages Area */}
                    <div className="flex-1 min-h-0 overflow-y-auto px-8 py-6 space-y-4 scroll-smooth">
                        {messages.length === 0 && (
                            <div className="h-full flex items-center justify-center">
                                <div className="text-center">
                                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-white/10 to-neutral-700/20 border border-white/10 flex items-center justify-center shadow-lg">
                                        <BookOpen className="w-8 h-8 text-white/70" />
                                    </div>
                                    <p className="text-neutral-300 text-lg font-semibold">Start a conversation</p>
                                    <p className="text-neutral-400 text-sm mt-2">Upload documents and ask questions to get started</p>
                                </div>
                            </div>
                        )}

                        {messages.map((msg, idx) => (
                            <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-slide-up`}>
                                <div className={`flex gap-3 max-w-2xl ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                                    {/* Avatar */}
                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg ${
                                        msg.role === "user"
                                            ? "bg-white"
                                            : "bg-gradient-to-br from-neutral-700 to-neutral-900 border border-white/10"
                                    }`}>
                                        {msg.role === "user" ? (
                                            <span className="text-black text-xs font-bold">U</span>
                                        ) : (
                                            <BookOpen className="w-4 h-4 text-white/70" />
                                        )}
                                    </div>

                                    {/* Message Bubble */}
                                    <div className={`px-5 py-3 rounded-2xl max-w-xl ${
                                        msg.role === "user"
                                            ? "bg-white text-black rounded-br-none shadow-lg shadow-white/20"
                                            : "bg-gradient-to-br from-neutral-900 to-neutral-800 text-white rounded-bl-none border border-white/10"
                                    }`}>
                                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                    </div>
                                </div>
                            </div>
                        ))}

                        {isTyping && (
                            <div className="flex justify-start animate-slide-up">
                                <div className="flex gap-3">
                                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-neutral-700 to-neutral-900 border border-white/10 flex items-center justify-center flex-shrink-0 shadow-lg">
                                        <BookOpen className="w-4 h-4 text-white/70" />
                                    </div>
                                    <div className="px-5 py-3 rounded-2xl bg-gradient-to-br from-neutral-900 to-neutral-800 border border-white/10 rounded-bl-none">
                                        <div className="flex gap-1.5">
                                            <div className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "0ms" }}></div>
                                            <div className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "150ms" }}></div>
                                            <div className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "300ms" }}></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={chatEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="px-8 py-6 border-t border-white/10 bg-gradient-to-r from-neutral-950/60 to-neutral-900/80 backdrop-blur-md">
                        <form onSubmit={handleSendMessage} className="flex items-center gap-3">
                            {/* Filter Button */}
                            <div className="relative" ref={filterMenuRef}>
                                <button
                                    type="button"
                                    onClick={() => setShowFilterMenu(!showFilterMenu)}
                                    disabled={availableFileTypes.length === 0}
                                    className="p-2.5 rounded-full bg-neutral-800 hover:bg-neutral-700 disabled:bg-neutral-800/40 disabled:cursor-not-allowed text-neutral-400 hover:text-white transition-all group relative border border-white/10 hover:border-white/25"
                                    title="Filter by file type"
                                >
                                    <Filter className="w-5 h-5" />
                                    {selectedFileTypes.length > 0 && (
                                        <span className="absolute top-0 right-0 w-5 h-5 bg-white text-black text-xs rounded-full flex items-center justify-center font-bold shadow-lg">
                                            {selectedFileTypes.length}
                                        </span>
                                    )}
                                </button>

                                {/* Filter Popover */}
                                {showFilterMenu && availableFileTypes.length > 0 && (
                                    <div className="absolute bottom-full left-0 mb-3 p-4 rounded-2xl bg-gradient-to-br from-neutral-950/95 to-neutral-900/90 border border-white/10 shadow-2xl w-56 z-50 animate-fade-in backdrop-blur-sm">
                                        <p className="text-xs font-semibold text-neutral-300 mb-3 uppercase tracking-widest">Search Scope</p>
                                        <div className="space-y-3">
                                            {availableFileTypes.map((ext) => (
                                                <label key={ext} className="flex items-center gap-3 cursor-pointer group">
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedFileTypes.includes(ext)}
                                                        onChange={() => {
                                                            setSelectedFileTypes(prev =>
                                                                prev.includes(ext) 
                                                                    ? prev.filter(t => t !== ext) 
                                                                    : [...prev, ext]
                                                            );
                                                        }}
                                                        className="w-4 h-4 rounded bg-neutral-800 border-white/20 text-white focus:ring-white/20 cursor-pointer accent-white"
                                                    />
                                                    <span className="text-sm text-neutral-300 uppercase tracking-wide group-hover:text-white transition-colors font-medium">.{ext}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Text Input */}
                            <input
                                type="text"
                                value={inputValue}
                                onChange={e => setInputValue(e.target.value)}
                                placeholder="Ask about your documents..."
                                disabled={isTyping}
                                className="flex-1 px-5 py-3 rounded-full bg-neutral-800 border border-white/10 text-white placeholder-neutral-500 focus:border-white/30 focus:ring-2 focus:ring-white/10 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                            />

                            {/* Send Button */}
                            <button
                                type="submit"
                                disabled={isTyping || !inputValue.trim()}
                                className="p-3 rounded-full bg-white hover:bg-neutral-200 disabled:bg-neutral-700 disabled:cursor-not-allowed text-black hover:shadow-lg shadow-lg shadow-white/20 disabled:shadow-none transition-all"
                                title="Send message"
                            >
                                <ArrowUp className="w-5 h-5" />
                            </button>
                        </form>
                    </div>
                </div>
            </main>
        </div>
    )
}

