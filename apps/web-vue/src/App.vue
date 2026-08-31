<template>
  <div>
    <header>
      <h1>Cortexo</h1>
      <p>LLM Research + Autonomous Software Engineering Infrastructure</p>
      <nav>
        <RouterLink to="/">Dashboard</RouterLink> |
        <RouterLink to="/repositories">Repositories</RouterLink> |
        <RouterLink to="/models">Models</RouterLink> |
        <RouterLink to="/arena">Arena</RouterLink> |
        <RouterLink to="/benchmarks">Benchmarks</RouterLink> |
        <RouterLink to="/agents">Agents</RouterLink> |
        <RouterLink to="/playground">Playground</RouterLink>
      </nav>
      <hr />
    </header>
    <main><RouterView /></main>
  </div>
</template>