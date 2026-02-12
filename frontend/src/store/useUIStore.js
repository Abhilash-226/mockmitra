/**
 * UI Store - Global UI state
 *
 * Manages: modals, toasts, theme, sidebar state
 */

import { create } from "zustand";

const useUIStore = create((set) => ({
  // Theme
  theme: "light",

  // Sidebar
  sidebarOpen: true,

  // Modal
  activeModal: null,
  modalData: null,

  // Toast notifications
  toasts: [],

  // Actions
  actions: {
    setTheme: (theme) => set({ theme }),

    toggleSidebar: () =>
      set((state) => ({
        sidebarOpen: !state.sidebarOpen,
      })),

    openModal: (modalId, data = null) =>
      set({
        activeModal: modalId,
        modalData: data,
      }),

    closeModal: () =>
      set({
        activeModal: null,
        modalData: null,
      }),

    addToast: (toast) =>
      set((state) => ({
        toasts: [...state.toasts, { id: Date.now(), ...toast }],
      })),

    removeToast: (id) =>
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      })),
  },
}));

// Named export for components using { useUIStore }
export { useUIStore };
export default useUIStore;
