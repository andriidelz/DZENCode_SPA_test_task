<template>
  <div id="app">
    <header>
      <nav class="navbar">
        <div class="navbar-brand">
          <h1>Comment System</h1>
        </div>
        <div class="navbar-nav">
          <router-link to="/" class="nav-link">Home</router-link>
          <router-link to="/comments" class="nav-link">Comments</router-link>
        </div>
      </nav>
    </header>
    
    <main class="main-content">
      <router-view />
    </main>
    
    <footer>
      <p>&copy; 2025 Comment System. Built with Vue.js</p>
    </footer>
  </div>
</template>

<script>
export default {
  name: 'App',
  mounted() {
    console.log('Comment System App loaded');
  }
}
</script>

<style>
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  padding: 20px;
}

footer {
  text-align: center;
  padding: 20px;
  background-color: #f8f9fa;
  margin-top: auto;
}
</style>
