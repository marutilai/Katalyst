# Ink + Python Hybrid Architecture for Katalyst

## Overview

This document outlines how to create a modern terminal UI for Katalyst using Node.js/Ink while keeping the existing Python backend intact. This approach gives us the best of both worlds: Claude Code-like terminal experience with React/Ink, while preserving all the Python agent logic.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Ink Terminal UI (Node.js)              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ Chat View   │  │ Mode Toggle  │  │ Status Bar     │ │
│  │ (React)     │  │ (Plan/Code)  │  │ (Progress)     │ │
│  └─────────────┘  └──────────────┘  └────────────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │            JSON-RPC Protocol Layer               │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────────┬───────────────┬────────────────────┘
                     │   stdin/out   │
                     ▼               ▼
┌─────────────────────────────────────────────────────────┐
│              Python Backend (Katalyst Core)              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ LangGraph   │  │ Agent Nodes  │  │ Tools          │ │
│  │ Orchestrator│  │ (Planner,    │  │ (file ops,    │ │
│  │             │  │  Executor)   │  │  search, etc) │ │
│  └─────────────┘  └──────────────┘  └────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Python Backend Adapter

Create a JSON-RPC server wrapper for Katalyst:

```python
# src/katalyst/app/jsonrpc_server.py
import sys
import json
import asyncio
from typing import Dict, Any
from katalyst.app.main import build_main_graph
from katalyst.katalyst_core.utils.logger import get_logger

class KatalystRPCServer:
    def __init__(self):
        self.graph = build_main_graph()
        self.logger = get_logger("rpc_server")
        self.current_mode = "plan"
        
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request from Ink UI."""
        method = request.get("method")
        params = request.get("params", {})
        id = request.get("id")
        
        try:
            if method == "chat":
                result = await self.handle_chat(params)
            elif method == "setMode":
                result = self.set_mode(params)
            elif method == "getStatus":
                result = self.get_status()
            else:
                raise ValueError(f"Unknown method: {method}")
                
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": id
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": id
            }
    
    async def handle_chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process chat message through Katalyst."""
        message = params.get("message")
        mode = params.get("mode", self.current_mode)
        
        # Configure based on mode
        if mode == "plan":
            # In plan mode, limit tools or add special instructions
            config = {"tools": ["read_file", "search_files"]}
        else:
            # In execute mode, full capabilities
            config = {}
        
        # Run through graph
        result = await self.graph.ainvoke({
            "task": message,
            "mode": mode,
            **config
        })
        
        return {
            "response": result.get("messages", [])[-1].content,
            "status": "complete",
            "filesModified": result.get("files_modified", [])
        }
    
    def run(self):
        """Main loop reading from stdin and writing to stdout."""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                    
                request = json.loads(line)
                response = asyncio.run(self.handle_request(request))
                
                # Write response with newline for proper streaming
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                
            except Exception as e:
                self.logger.error(f"RPC Server error: {e}")
```

### Phase 2: Ink Terminal UI

Create the Node.js/Ink frontend:

```javascript
// katalyst-ui/src/App.js
import React, { useState, useEffect } from 'react';
import { Box, Text, useInput } from 'ink';
import { PythonShell } from 'python-shell';
import ChatView from './components/ChatView';
import StatusBar from './components/StatusBar';
import ModeIndicator from './components/ModeIndicator';

const KatalystUI = () => {
    const [messages, setMessages] = useState([]);
    const [mode, setMode] = useState('plan');
    const [isProcessing, setIsProcessing] = useState(false);
    const [pyshell, setPyshell] = useState(null);
    
    useEffect(() => {
        // Initialize Python backend
        const shell = new PythonShell('../src/katalyst/app/jsonrpc_server.py', {
            mode: 'json',
            pythonOptions: ['-u']
        });
        
        shell.on('message', (response) => {
            handleResponse(response);
        });
        
        setPyshell(shell);
        
        return () => {
            shell.kill();
        };
    }, []);
    
    useInput((input, key) => {
        if (key.ctrl && input === 'm') {
            toggleMode();
        }
    });
    
    const toggleMode = () => {
        const newMode = mode === 'plan' ? 'execute' : 'plan';
        setMode(newMode);
        
        if (pyshell) {
            pyshell.send({
                jsonrpc: "2.0",
                method: "setMode",
                params: { mode: newMode },
                id: Date.now()
            });
        }
    };
    
    const sendMessage = (message) => {
        setIsProcessing(true);
        
        // Add user message to UI
        setMessages(prev => [...prev, {
            type: 'user',
            content: message,
            timestamp: new Date()
        }]);
        
        // Send to Python backend
        if (pyshell) {
            pyshell.send({
                jsonrpc: "2.0",
                method: "chat",
                params: { 
                    message,
                    mode 
                },
                id: Date.now()
            });
        }
    };
    
    const handleResponse = (response) => {
        if (response.result) {
            setMessages(prev => [...prev, {
                type: 'assistant',
                content: response.result.response,
                timestamp: new Date()
            }]);
        }
        setIsProcessing(false);
    };
    
    return (
        <Box flexDirection="column" height="100%">
            <Box borderStyle="round" paddingX={1}>
                <ModeIndicator mode={mode} />
                <Text> | </Text>
                <Text>Ctrl+M: Toggle Mode | Ctrl+C: Exit</Text>
            </Box>
            
            <Box flexGrow={1} borderStyle="single" margin={1}>
                <ChatView 
                    messages={messages}
                    onSendMessage={sendMessage}
                    isProcessing={isProcessing}
                />
            </Box>
            
            <StatusBar 
                mode={mode}
                isProcessing={isProcessing}
            />
        </Box>
    );
};

export default KatalystUI;
```

### Phase 3: Component Library

Build Ink components matching Claude Code's UI:

```javascript
// katalyst-ui/src/components/ChatView.js
import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';
import Spinner from 'ink-spinner';
import Markdown from './Markdown';

const ChatView = ({ messages, onSendMessage, isProcessing }) => {
    const [input, setInput] = useState('');
    
    useInput((key, data) => {
        if (data.key === 'return' && input.trim() && !isProcessing) {
            onSendMessage(input);
            setInput('');
        } else if (data.key === 'backspace') {
            setInput(input.slice(0, -1));
        } else if (!data.ctrl && !data.meta && data.key) {
            setInput(input + data.key);
        }
    });
    
    return (
        <Box flexDirection="column" height="100%">
            <Box flexGrow={1} flexDirection="column" paddingX={1}>
                {messages.map((msg, idx) => (
                    <Box key={idx} marginY={1}>
                        {msg.type === 'user' ? (
                            <Text bold color="cyan">&gt; {msg.content}</Text>
                        ) : (
                            <Box flexDirection="column">
                                <Markdown content={msg.content} />
                            </Box>
                        )}
                    </Box>
                ))}
                
                {isProcessing && (
                    <Box>
                        <Text color="yellow">
                            <Spinner type="dots" /> Thinking...
                        </Text>
                    </Box>
                )}
            </Box>
            
            <Box borderStyle="single" paddingX={1}>
                <Text>&gt; </Text>
                <Text>{input}</Text>
                <Text color="gray">│</Text>
            </Box>
        </Box>
    );
};
```

## Key Benefits

1. **Modern UI**: React-based terminal UI with smooth updates
2. **Familiar DX**: Frontend devs can contribute using React
3. **Clean Separation**: UI logic separate from agent logic
4. **Easy Theming**: CSS-in-JS style components
5. **Rich Features**: Animations, spinners, progress bars out of the box

## Migration Path

1. **Keep existing CLI**: Add `--ui=classic` flag for current interface
2. **New default**: Make Ink UI the default with `katalyst` command
3. **Gradual adoption**: Users can switch between UIs as needed
4. **Backward compatible**: All Python logic remains unchanged

## Technical Considerations

### Communication Protocol
- JSON-RPC 2.0 for structured communication
- Streaming responses for real-time updates
- Error handling and reconnection logic

### State Management
- UI state in React/Ink
- Agent state in Python
- Minimal state sync between layers

### Performance
- Lazy loading of Python backend
- Efficient message passing
- Debounced UI updates

## Example Commands

```bash
# Install Ink UI
cd katalyst-ui
npm install

# Run with Ink UI (default)
katalyst

# Run with classic Python UI
katalyst --ui=classic

# Development mode
npm run dev  # Ink UI with hot reload
```

## Future Enhancements

1. **Split Panes**: File explorer + chat view
2. **Syntax Highlighting**: Better code display
3. **Mouse Support**: Click to navigate
4. **Themes**: Dark/light/custom themes
5. **Plugins**: Extensible UI components

This hybrid approach gives us the best possible terminal experience while maintaining all existing functionality. The Python backend remains untouched, making this a low-risk, high-reward improvement.