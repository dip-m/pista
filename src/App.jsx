import React from "react";
import PistaChat from "./components/PistaChat";

function App() {
  const user = { id: "demo-user-123" };

  return (
    <div className="App">
      <h1>Pista – Game Sommelier</h1>
      <PistaChat user={user} />
    </div>
  );
}

export default App;
