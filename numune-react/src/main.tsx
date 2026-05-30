/**
 * Mount adapter — Flask tarafından çağrılır.
 *
 * Kullanım (urun.html teknik sekmesi):
 *   const el = document.getElementById("numune-root");
 *   const instance = window.NumuneApp.mount(el, {
 *     initialState: { desen: ..., tarak: ... },
 *     urunId: "...",
 *     surumId: "v1",
 *     onChange: (state) => {  // debounced 500 ms
 *       fetch(`/api/urun/${urunId}/teknik/${surumId}`, {
 *         method: "POST",
 *         body: JSON.stringify({
 *           tahar_grid: state.desen,
 *           tarak_raporu: state.tarak,
 *         }),
 *       });
 *     },
 *   });
 *
 *   // Sürüm değişiminde:
 *   instance.update({ initialState: { desen, tarak }, surumId });
 *
 *   // Cleanup:
 *   instance.unmount();
 */
import "./index.css";
import { createRoot } from "react-dom/client";
import type { Root } from "react-dom/client";
import { App } from "./App";
import type { DesenState, TarakState } from "./lib/types";

export interface MountOpts {
  initialState: { desen?: DesenState | unknown; tarak?: TarakState | unknown };
  urunId: string;
  surumId: string;
  onChange?: (state: { desen: DesenState; tarak: TarakState }) => void;
}

export interface MountInstance {
  unmount: () => void;
  update: (opts: Partial<MountOpts>) => void;
}

interface NumuneAppGlobal {
  mount: (el: HTMLElement, opts: MountOpts) => MountInstance;
}

declare global {
  interface Window {
    NumuneApp: NumuneAppGlobal;
  }
}

const api: NumuneAppGlobal = {
  mount(el, opts) {
    const root: Root = createRoot(el);
    let current = opts;

    const render = () => {
      root.render(
        <App
          key={current.surumId /* sürüm değişince state remount */}
          initialState={current.initialState}
          urunId={current.urunId}
          surumId={current.surumId}
          onChange={current.onChange}
        />,
      );
    };

    render();

    return {
      unmount: () => root.unmount(),
      update: (partial) => {
        current = { ...current, ...partial };
        render();
      },
    };
  },
};

window.NumuneApp = api;

// Vite library mode bundle olarak da export
export default api;
