// src/app/page.tsx
'use client';

import { useSession, signIn, signOut } from 'next-auth/react';
import { useState, useEffect, useRef, FormEvent } from 'react';

type Mensaje = { de: 'usuario' | 'bot'; texto: string };

export default function Page() {
  const { data: session } = useSession();
  const [chat, setChat] = useState<Mensaje[]>([]);
  const [msg, setMsg] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  // Estado para efecto máquina de escribir
  const [typingText, setTypingText] = useState<string | null>(null);
  const [typingIndex, setTypingIndex] = useState<number>(0);
  const typingWordsRef = useRef<string[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll al final del chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat, typingIndex]);

  // Efecto máquina de escribir: palabra por palabra
  useEffect(() => {
    if (typingText === null) return;

    const words = typingWordsRef.current;
    if (typingIndex >= words.length) {
      // Terminó de escribir, agregar mensaje completo al chat
      setChat((c) => [...c, { de: 'bot', texto: typingText }]);
      setTypingText(null);
      setTypingIndex(0);
      typingWordsRef.current = [];
      return;
    }

    const timer = setTimeout(() => {
      setTypingIndex((prev) => prev + 1);
    }, 60); // velocidad: 60ms por palabra

    return () => clearTimeout(timer);
  }, [typingText, typingIndex]);

  // Si no hay sesión, mostramos botón de login
  if (!session) {
    return (
      <div className="h-full flex items-center justify-center">
        <button
          onClick={() => signIn('google')}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-lg flex items-center gap-2"
        >
          Login con Google
        </button>
      </div>
    );
  }

  // Función para enviar mensaje
  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    if (!msg) return;
    setLoading(true);

    // Agregar mensaje del usuario inmediatamente
    setChat((c) => [...c, { de: 'usuario', texto: msg }]);
    const mensajeEnviado = msg;
    setMsg('');

    const userEmail = session.user?.email ?? '';
    const res = await fetch(
      `/api/agent?idagente=${encodeURIComponent(userEmail)}&msg=${encodeURIComponent(mensajeEnviado)}`
    );

    // Parsear la respuesta JSON del backend
    let respuestaBot = '';
    try {
      const data = await res.json();
      respuestaBot = data.response ?? JSON.stringify(data);
    } catch {
      respuestaBot = await res.text();
    }

    // Iniciar efecto máquina de escribir
    const words = respuestaBot.split(/(\s+)/); // preservar espacios
    typingWordsRef.current = words;
    setTypingText(respuestaBot);
    setTypingIndex(0);
    setLoading(false);
  };

  // Texto parcial para el efecto de escritura
  const displayedTyping =
    typingText !== null
      ? typingWordsRef.current.slice(0, typingIndex).join('')
      : null;

  return (
    <div className="h-full flex flex-col p-4 text-black">
      <header className="mb-4 flex justify-between items-center">
        <div>
          <span className="font-medium">¡Hola, {session.user?.email}!</span>
        </div>
        <button
          onClick={() => signOut()}
          className="text-sm text-gray-600 hover:underline"
        >
          Cerrar sesión
        </button>
      </header>

      <div className="flex-1 overflow-y-auto space-y-3 pb-4">
        {chat.map((m, i) => (
          <div
            key={i}
            className={`p-3 rounded max-w-[70%] whitespace-pre-wrap ${
              m.de === 'usuario'
                ? 'ml-auto bg-gray-200 text-right'
                : 'mr-auto bg-gray-100'
            }`}
          >
            {m.texto}
          </div>
        ))}

        {/* Mensaje del bot escribiéndose */}
        {displayedTyping !== null && (
          <div className="p-3 rounded max-w-[70%] whitespace-pre-wrap mr-auto bg-gray-100">
            {displayedTyping}
            <span className="inline-block w-1 h-4 bg-black ml-1 animate-pulse" />
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      <form onSubmit={enviar} className="mt-2 flex gap-2">
        <input
          className="flex-1 rounded border px-3 py-2"
          placeholder="Escribe tu mensaje…"
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          disabled={loading || typingText !== null}
          required
        />
        <button
          type="submit"
          disabled={loading || typingText !== null}
          className="bg-black hover:bg-gray-800 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {loading ? '…' : 'Enviar'}
        </button>
      </form>
    </div>
  );
}
